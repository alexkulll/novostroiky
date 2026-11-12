import json
import re
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation
from selection import select_complexes, MIN_AREA, MAX_AREA
from assistant_prompts import SYSTEM_PROMPT, DIALOGUE_PROMPT
from launch_ai import ensure_server

ENDPOINT = 'http://127.0.0.1:8080/v1/chat/completions'
CITIES = {'моск': 'Москва', 'сочи': 'Сочи', 'екатеринбург': 'Екатеринбург', 'екб': 'Екатеринбург'}

class AssistantUnavailable(Exception):
    pass

def extract_query(message, state, requester=None):
    if requester is None:
        try:
            ensure_server()
        except (RuntimeError, OSError) as exc:
            raise AssistantUnavailable(str(exc)) from exc
        requester = urllib.request.urlopen
    context = {'waiting_for_area': bool(state.get('city') and state.get('budget') and not state.get('area'))}
    payload = {'model': 'local-qwen', 'temperature': 0.0, 'max_tokens': 280,
               'response_format': {'type': 'json_object'},
               'messages': [{'role': 'system', 'content': SYSTEM_PROMPT},
                            {'role': 'user', 'content': 'Контекст программы: ' + json.dumps(context, ensure_ascii=False) + '\nПоследнее сообщение пользователя: ' + message}]}
    req = urllib.request.Request(ENDPOINT, json.dumps(payload, ensure_ascii=False).encode('utf-8'), {'Content-Type': 'application/json'}, method='POST')
    try:
        with requester(req, timeout=90) as r:
            response = json.loads(r.read().decode('utf-8'))
        text = response['choices'][0]['message']['content'].strip()
        if text.startswith('```'):
            text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text, flags=re.I)
        parsed = json.loads(text)
        if not isinstance(parsed, dict): raise ValueError('Expected JSON object')
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise AssistantUnavailable('Не удалось получить корректный ответ локальной модели. Проверьте, запущен ли сервер llama.cpp.') from exc
    result = {'intent': parsed.get('intent') if parsed.get('intent') in {'search', 'list', 'details', 'other'} else 'other'}
    for key in ('city_quote', 'budget_quote', 'area_quote', 'complex_quote'):
        quote = parsed.get(key)
        result[key] = quote.strip() if isinstance(quote, str) and quote.strip() and quote.strip().casefold() in message.casefold() else None
    return result

def parse_amount(quote, *, area=False):
    if not quote: return None
    normalized = quote.casefold().replace('\u00a0', ' ')
    if area:
        normalized = re.sub(r'(?i)(?:кв\.?\s*)?[мm]\s*(?:²|2)\b|(?:кв\.?\s*)?[мm]²', ' ', normalized)
    matches = re.findall(r'\d[\d\s]*(?:[.,]\d+)?', normalized)
    if len(matches) != 1: return None
    number = re.sub(r'\s+', '', matches[0]).replace(',', '.')
    try: value = Decimal(number)
    except InvalidOperation: return None
    if not area:
        if re.search(r'млрд|миллиард', normalized): value *= 1000000000
        elif re.search(r'млн|миллион', normalized): value *= 1000000
        elif re.search(r'тыс|тысяч', normalized): value *= 1000
    if not value.is_finite() or value <= 0 or value > (Decimal('10000') if area else Decimal('1000000000000')): return None
    return value

def city_from_quote(quote):
    if not quote: return None
    value = quote.casefold().replace('ё','е')
    return next((city for root, city in CITIES.items() if root in value), None)

def money(value):
    return f'{int(value):,}'.replace(',', ' ')

def answer(message, state, rows, extractor=extract_query):
    message = message.strip()
    if not message: return 'Напишите вопрос, и я постараюсь помочь.', dict(state)
    if len(message)>1000: return 'Пожалуйста, задайте вопрос короче.', dict(state)
    data = extractor(message, state)
    updated = dict(state)
    if data.get('city_quote'):
        resolved=city_from_quote(data['city_quote'])
        if not resolved: return 'В нашей базе есть Москва, Сочи и Екатеринбург. Какой город вам интересен?', updated
        updated['city']=resolved
    for field, key, is_area in [('budget_quote','budget',False),('area_quote','area',True)]:
        if data.get(field):
            value=parse_amount(data[field], area=is_area)
            if value is None:
                if is_area:
                    updated.pop('area', None)
                return 'Не удалось распознать число. Укажите бюджет в рублях и площадь в м².', updated
            if is_area and not MIN_AREA <= value <= MAX_AREA:
                updated.pop('area', None)
                return ('Такая площадь вне диапазона подбора. Укажите площадь от 10 до 1000 м². '
                        'Доступность конкретной площади в ЖК нужно уточнять отдельно.'), updated
            updated[key]=str(value)
    if data['intent']=='other' and not any(data.get(k) for k in ('city_quote','budget_quote','area_quote','complex_quote')):
        return 'Я помогу выбрать ЖК в Москве, Сочи или Екатеринбурге и расскажу о данных из нашей таблицы. Укажите город или название ЖК.', updated
    if data['intent']=='details':
        quote=(data.get('complex_quote') or '').casefold()
        matches=[x for x in rows if quote and (quote in x['complex_name'].casefold() or x['complex_name'].casefold() in quote)]
        if len(matches)!=1:return 'Напишите название ЖК из нашей базы, и я покажу известные сведения.',updated
        x=matches[0]
        return (f"**{x['complex_name']}** — {x['city']}, {x['district_address']}. Застройщик: {x['developer']}; класс: {x['class']}. Цена от {money(x['price_per_sqm'])} ₽/м²; срок: {x['completion']}. [Источник]({x['source_url']})"), updated
    if not updated.get('city'):
        return 'Какой город вам интересен: Москва, Сочи или Екатеринбург?',updated
    city=updated['city']
    candidates=[x for x in rows if x['city']==city]
    if updated.get('budget') and not updated.get('area'):
        budget = Decimal(updated['budget'])
        if candidates and all(Decimal(x['price_per_sqm']) * MIN_AREA > budget for x in candidates):
            return ('По указанному бюджету вариантов в нашей таблице не найдено даже при минимальной '
                    'площади, которую принимает подбор. Попробуйте увеличить бюджет.'), updated
        return ('Бюджет учтён. Чтобы определить подходящие ЖК, укажите желаемую площадь в м².'), updated
    if (data['intent']=='list' and not data.get('budget_quote') and not data.get('area_quote')) or not updated.get('area'):
        lines=[f"- **{x['complex_name']}** — от {money(x['price_per_sqm'])} ₽/м²" for x in candidates]
        note = ('Чтобы рассчитать стоимость, укажите желаемую площадь в м² и бюджет.'
                if not updated.get('area') else 'Могу подобрать варианты по вашему бюджету и площади.')
        return f'Вот ЖК в нашей базе: **{city}**.\n\n'+'\n'.join(lines)+'\n\n'+note,updated
    if not updated.get('budget'):
        return 'Какой у вас бюджет на квартиру в рублях?',updated
    results=select_complexes(rows,city,updated['budget'],updated['area'])
    if not results:
        return 'По вашему городу, бюджету и площади подходящих вариантов в нашей таблице не найдено. Попробуйте изменить бюджет или площадь.',updated
    lines=[f"- **{x['complex_name']}** — примерно {money(x['estimated_price'])} ₽ ([источник]({x['source_url']}))" for x in results]
    return 'По вашим параметрам в нашей выборке подходят:\n\n'+'\n'.join(lines)+'\n\nОценка рассчитана как площадь × цена от за м². Наличие квартиры такой площади и её фактическую стоимость нужно уточнить.',updated


_NUMBER_WORDS = re.compile(r"(?:\d|[ⅰ-ⅿⅠ-Ⅿ]|\b(?:ноль|один|одна|одно|одну|перв\w*|втор\w*|трет\w*|четвер\w*|две|два|три|четыре|пять|шесть|семь|восемь|девять|десять|одиннадцать|двенадцать|тринадцать|четырнадцать|пятнадцать|шестнадцать|семнадцать|восемнадцать|девятнадцать|двадцать|тридцать|сорок|пятьдесят|шестьдесят|семьдесят|восемьдесят|девяносто|сто|двести|триста|четыреста|пятьсот|шестьсот|семьсот|восемьсот|девятьсот|пара|тысяч\w*|миллион\w*|миллиард\w*|полмиллион\w*|половин\w*|процент\w*)\b)", re.IGNORECASE)

def conversational_text(message, facts):
    payload = {'model':'local-qwen','temperature':0.55,'max_tokens':140,
      'messages':[{'role':'system','content':DIALOGUE_PROMPT},
                  {'role':'user','content':json.dumps({'вопрос':message,'факты':facts},ensure_ascii=False)}]}
    req=urllib.request.Request(ENDPOINT,json.dumps(payload,ensure_ascii=False).encode('utf-8'),{'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=90) as r: data=json.loads(r.read().decode('utf-8'))
        text=data['choices'][0]['message']['content'].strip()
        if not text or len(text)>650: return ''
        sentences = re.split(r'(?<=[.!?])\s+', text)
        safe = []
        for sentence in sentences:
            if ('?' in sentence or _NUMBER_WORDS.search(sentence)
                or re.search(r'\b(?:уточните|уточни|укажите|укажи|скажите|скажи|напишите|напиши|назовите|назови|сообщите|сообщи|подскажите|подскажи|расскажите|расскажи)\b', sentence, re.I)
                or re.search(r'\b(?:достаточ\w*|хватит|вписыва\w*|подойд\w*|доступн\w*)\b|\b(?:можно|получится|удастся|найд[её]тся)\b.{0,80}\b(?:выбрать|подобрать|найти|купить|приобрести|квартир\w*)\b', sentence, re.I)):
                continue
            safe.append(sentence)
        return ' '.join(safe).strip()
    except (OSError,ValueError,KeyError,IndexError,TypeError):
        return ''

def reply(message, state, rows):
    facts, updated = answer(message, state, rows)
    if re.search(r'отзыв|отклик|впечатлени[яйе]|мнение жильц', message, flags=re.I):
        facts += ('\n\n**Реальных отзывов в нашей базе нет.** '
                  'Вымышленный пример мнения, не отзыв покупателя: '
                  '«Я бы рассмотрел этот вариант и уточнил детали перед покупкой».')
    restricted = ('вне диапазона подбора' in facts or 'не удалось распознать' in facts.lower()
                  or 'не найдено' in facts or 'определить подходящие ЖК' in facts)
    friendly = '' if restricted else conversational_text(message,facts)
    by_name = {row['complex_name']: row for row in rows}
    cards = []
    remaining = []
    for line in facts.splitlines():
        match = re.match(r'^- \*\*(.+?)\*\* — (.+)$', line)
        if match and match.group(1) in by_name:
            summary = re.sub(r'\s*\(\[источник\]\(.*?\)\)', '', match.group(2)).strip()
            cards.append({'id': by_name[match.group(1)]['id'], 'name': match.group(1), 'summary': summary})
        else:
            detail = re.match(r'^\*\*(.+?)\*\* — ', line)
            if detail and detail.group(1) in by_name:
                row = by_name[detail.group(1)]
                cards.append({'id': row['id'], 'name': row['complex_name'], 'summary': f"от {money(row['price_per_sqm'])} ₽/м²"})
            remaining.append(line)
    body = '\n'.join(remaining).strip()
    return (friendly+'\n\n'+body if friendly else body), updated, cards
