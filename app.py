import base64

import streamlit as st
import streamlit.components.v1 as components
import pydeck as pdk
from selection import ROOT, load_complexes, select_complexes
from assistant_service import reply, AssistantUnavailable
from mortgage import calculate_mortgage
from property_cards import render_photo, render_details

st.set_page_config(page_title='Атлас | Новостройки', page_icon='◈', layout='wide', initial_sidebar_state='collapsed')

background_path = ROOT / 'images' / '01.png'
background = base64.b64encode(background_path.read_bytes()).decode('ascii') if background_path.is_file() else ''
st.markdown(f'''<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
:root {{ color-scheme: dark; }}
.stApp {{ color: #f1f3f0; background: #0b1013; font-family: 'Manrope', sans-serif; }}
.stApp::before {{ content: ''; position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background: linear-gradient(90deg, rgba(8,13,16,.97) 0%, rgba(9,14,17,.91) 46%, rgba(8,13,16,.80) 100%), url('data:image/png;base64,{background}') center center / cover no-repeat; }}
[data-testid="stHeader"] {{ background: #0b1013 !important; }}
[data-testid="stAppViewContainer"] > .main {{ background: transparent; }}
[data-testid="stAppViewBlockContainer"] {{ max-width: 1310px; padding-top: 2rem; padding-bottom: 5rem; position: relative; }}
[data-testid="stHeaderActionElements"], #MainMenu, footer {{ visibility: hidden; }}
.brandbar {{ display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(231,238,231,.16); padding-bottom:18px; margin-bottom:62px; }}
.brand {{ display:flex; align-items:center; gap:11px; color:#f3f3ed; font-size:16px; font-weight:800; letter-spacing:.18em; }}
.brand-icon {{ color:#c5e3a3; font-size:22px; }}
.brand-note {{ color:#a6b0ab; font-size:11px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; }}
.eyebrow {{ color:#c6e3a8; text-transform:uppercase; letter-spacing:.19em; font-size:11px; font-weight:800; margin:0 0 17px; }}
.hero-title {{ font-size:clamp(40px,5.4vw,70px); line-height:1.06; letter-spacing:-.055em; color:#f4f5ef; font-weight:600; margin:0 0 18px; max-width:800px; }}
.hero-title span {{ color:#c9e6ab; }}
.hero-description {{ color:#b5c0ba; font-size:16px; line-height:1.7; max-width:600px; margin:0 0 42px; }}
.section-kicker {{ color:#c5e3a3; font-size:11px; text-transform:uppercase; letter-spacing:.16em; font-weight:700; margin:0 0 10px; }}
.section-title {{ color:#f5f6f0; font-size:24px; letter-spacing:-.035em; font-weight:700; margin:0 0 8px; }}
.section-copy {{ color:#9fac9f; font-size:13px; line-height:1.6; margin:0 0 16px; }}
[data-testid="stForm"] {{ background:rgba(21,29,30,.87); border:1px solid rgba(219,235,219,.14); padding:25px; border-radius:16px; }}
[data-testid="stForm"] label {{ color:#d0d9d0 !important; font-size:13px !important; font-weight:600; }}
[data-baseweb="select"] > div, [data-baseweb="input"] {{ background: #202c2d !important; border-color: #3b4a46 !important; border-radius:9px !important; }}
[data-testid="stFormSubmitButton"] button {{ background:#c9e6a7; color:#142019; border:0; border-radius:9px; font-weight:800; min-height:48px; }}
[data-testid="stFormSubmitButton"] button:hover {{ background:#e0f3c7; color:#142019; border:0; }}
[data-testid="stVerticalBlockBorderWrapper"] > div {{ background:rgba(23,32,32,.94); border-color:rgba(215,234,211,.16) !important; border-radius:16px; }}
.assistant-label {{ display:flex; align-items:center; gap:9px; font-size:11px; color:#c7e5a8; font-weight:800; letter-spacing:.15em; text-transform:uppercase; margin-bottom:24px; }}
.assistant-dot {{ width:8px; height:8px; border-radius:50%; background:#bddc9d; box-shadow:0 0 14px #bddc9d; }}
.assistant-title {{ font-size:22px; font-weight:700; letter-spacing:-.04em; color:#f2f4ed; margin:0 0 14px; }}
.assistant-text {{ color:#aebdb0; font-size:14px; line-height:1.75; margin:0 0 22px; }}
.assistant-status {{ border-top:1px solid rgba(222,239,218,.13); padding-top:16px; color:#a5b4a6; font-size:12px; line-height:1.6; }}
[data-testid="stExpander"] {{ background:rgba(22,31,31,.88); border:1px solid rgba(219,235,219,.14); border-radius:14px; }}
[data-testid="stImage"] img {{ border-radius:10px; object-fit:cover; }}
[data-testid="stCaptionContainer"] {{ color:#a8b5aa; }}
[data-testid="InputInstructions"] {{ display: none !important; }}
@media(max-width: 700px) {{ [data-testid="stAppViewBlockContainer"] {{ padding-top:1.3rem; }} .brandbar {{ margin-bottom:38px; }} .brand-note {{ display:none; }} .hero-title {{ font-size:42px; }} }}
</style>''', unsafe_allow_html=True)

try:
    properties = load_complexes()
except (OSError, ValueError) as exc:
    st.error(f'Не удалось загрузить данные: {exc}')
    st.stop()

st.markdown('''<div class="brandbar"><div class="brand"><span class="brand-icon">◈</span> АТЛАС</div><div class="brand-note">Подбор новостроек · Москва / Сочи / Екатеринбург</div></div>
<div class="eyebrow">Недвижимость, которая подходит вам</div>
<div class="hero-title">Найдите место<br>для <span>новой жизни.</span></div>
<div class="hero-description">Выберите город, задайте бюджет и площадь — мы покажем жилые комплексы, которые подходят под ваш запрос.</div>''', unsafe_allow_html=True)

def show_on_map(city, complex_id):
    st.session_state['map_city'] = city
    st.session_state['map_focus'] = complex_id
    st.session_state['map_expanded'] = True
    st.session_state['scroll_to_map'] = True
    st.session_state['map_revision'] = st.session_state.get('map_revision', 0) + 1


def change_map_city():
    st.session_state.pop('map_focus', None)


def change_catalog_city():
    st.session_state.pop('catalog_open_city', None)


main, side = st.columns([1.75, 1], gap='large')
with main:
    st.markdown('<div class="section-kicker">01 / Ваши параметры</div><div class="section-title">Начнём с главного</div><div class="section-copy">Три параметра — и подборка готова.</div>', unsafe_allow_html=True)
    with st.form('search'):
        city = st.selectbox('Город', sorted({row['city'] for row in properties}))
        left, right = st.columns(2)
        with left:
            budget = st.number_input('Бюджет на квартиру, ₽', min_value=1, value=30000000, step=1000000)
        with right:
            area = st.number_input('Желаемая площадь, м²', min_value=10.0, max_value=1000.0, value=50.0, step=1.0)
        submitted = st.form_submit_button('Показать подходящие ЖК  ↗', type='primary', use_container_width=True)
    if submitted:
        st.session_state['search_query'] = {'city': city, 'budget': budget, 'area': area}
        st.session_state.pop('map_focus', None)
        st.session_state['map_expanded'] = False
        st.session_state['map_revision'] = st.session_state.get('map_revision', 0) + 1
    query = st.session_state.get('search_query')
    if query:
        results = select_complexes(properties, **query)
        st.markdown('<div class="section-kicker" style="margin-top:38px">02 / Результаты</div>', unsafe_allow_html=True)
        st.subheader('Ваша подборка')
        st.caption('Ориентировочная стоимость = площадь × цена от за м². Наличие квартиры и итоговую цену уточняйте у продавца.')
        if not results:
            st.warning('Подходящих вариантов пока нет. Попробуйте изменить бюджет или площадь.')
        for row in results:
            with st.container(border=True):
                photo, details = st.columns([1, 1.6], gap='medium')
                with photo:
                    render_photo(row, show_placeholder=True)
                with details:
                    render_details(row, 'search', show_on_map, heading=True, estimate=row['estimated_price'])
    st.write('')
    st.markdown('<div class="section-kicker" style="margin-top:30px">Все объекты</div><div class="section-title">Изучите жилые комплексы</div><div class="section-copy">Выберите город и откройте каталог, чтобы увидеть все объекты нашей подборки.</div>', unsafe_allow_html=True)
    catalog_city = st.selectbox('Город для просмотра ЖК', sorted({row['city'] for row in properties}), key='catalog_city', on_change=change_catalog_city)
    if st.button('Смотреть все ЖК', key='show_catalog', use_container_width=True):
        st.session_state['catalog_open_city'] = catalog_city
    if st.session_state.get('catalog_open_city') == catalog_city:
        catalog_rows = [row for row in properties if row['city'] == catalog_city]
        st.caption(f'Жилых комплексов в подборке: {len(catalog_rows)}')
        for row in catalog_rows:
            with st.expander(row['complex_name'], expanded=False):
                photo, details = st.columns([1, 1.5], gap='medium')
                with photo:
                    render_photo(row)
                with details:
                    render_details(row, 'catalog', show_on_map)

    st.write('')
    st.markdown('<div class="section-kicker" style="margin-top:28px">Исследуйте город</div>', unsafe_allow_html=True)
    st.markdown('<div id="property-map-anchor"></div>', unsafe_allow_html=True)
    with st.expander('◉   Посмотреть ЖК на карте', expanded=st.session_state.get('map_expanded', False)):
        map_city = st.selectbox('Город на карте', sorted({row['city'] for row in properties}), key='map_city', on_change=change_map_city)
        city_rows = [row for row in properties if row['city'] == map_city and row['latitude'] and row['longitude']]
        points = [{'id': row['id'], 'name': row['complex_name'], 'lat': float(row['latitude']), 'lon': float(row['longitude']), 'color': [255, 192, 94, 255] if row['id'] == st.session_state.get('map_focus') else [198, 232, 164, 235]} for row in city_rows]
        if points:
            st.caption('Нажмите на точку, чтобы открыть карточку жилого комплекса.')
            center_lat = sum(point['lat'] for point in points) / len(points)
            center_lon = sum(point['lon'] for point in points) / len(points)
            layer = pdk.Layer(
                'ScatterplotLayer', id='complexes', data=points,
                get_position='[lon, lat]', get_fill_color='color',
                get_line_color=[255, 255, 255, 220], get_radius=180,
                radius_min_pixels=9, radius_max_pixels=15, stroked=True,
                line_width_min_pixels=2, pickable=True, auto_highlight=True,
            )
            deck = pdk.Deck(
                layers=[layer], map_style=None,
                initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=10, pitch=0),
                tooltip={'text': '{name}'},
            )
            event = st.pydeck_chart(deck, key='map_' + map_city + '_' + str(st.session_state.get('map_revision', 0)), on_select='rerun', selection_mode='single-object', height=450)
            selected = event.selection.objects.get('complexes', [])
            selected_id = selected[0].get('id') if selected else st.session_state.get('map_focus')
            selected_row = next((row for row in city_rows if row['id'] == selected_id), None)
            if selected_row:
                with st.container(border=True):
                    photo, details = st.columns([1, 1.5], gap='medium')
                    with photo:
                        render_photo(selected_row)
                    with details:
                        render_details(selected_row, 'map', heading=True)
            else:
                st.caption('Выберите точку на карте, чтобы увидеть фото и данные ЖК.')
        else:
            st.caption('Для этого города пока нет координат.')


    if st.session_state.pop('scroll_to_map', False):
        components.html(f"<script>window.mapNavigationRevision={st.session_state['map_revision']}</script>" + """<script>
          let tries = 0;
          function scrollToMap() {
            try {
              const anchor = window.parent.document.getElementById('property-map-anchor');
              if (anchor) { anchor.scrollIntoView({behavior: 'smooth', block: 'start'}); return; }
            } catch (error) { console.warn('Map navigation unavailable', error); return; }
            if (++tries < 20) setTimeout(scrollToMap, 100);
          }
          setTimeout(scrollToMap, 150);
        </script>""", height=0)

with side:
    with st.container(border=True):
        st.markdown('''<div class="assistant-label"><span class="assistant-dot"></span> AI-АССИСТЕНТ</div>
        <div class="assistant-title">Помогу с выбором</div>
        <div class="assistant-text">Спросите о ЖК в нашей базе или напишите, какой город и бюджет вам подходят.</div>''', unsafe_allow_html=True)
        if 'assistant_messages' not in st.session_state:
            st.session_state['assistant_messages'] = []
        if 'assistant_context' not in st.session_state:
            st.session_state['assistant_context'] = {}
        for message_index, item in enumerate(st.session_state['assistant_messages']):
            with st.chat_message(item['role']):
                st.markdown(item['content'])
                for card in item.get('cards', []):
                    property_row = next((r for r in properties if r['id'] == card['id']), None)
                    if not property_row:
                        continue
                    with st.popover(card['name'] + ' · ' + card['summary'], use_container_width=True):
                        render_photo(property_row)
                        render_details(property_row, f'assistant_{message_index}', show_on_map)
        with st.form('assistant_form', clear_on_submit=True):
            question = st.text_input('Ваш вопрос', placeholder='Например: ЖК в Екатеринбурге до 20 млн', max_chars=1000)
            send = st.form_submit_button('Отправить', use_container_width=True)
        if send and question.strip():
            st.session_state['assistant_messages'].append({'role':'user','content':question.strip()})
            with st.spinner('Запускаю модель при необходимости и готовлю ответ...'):
                try:
                    response, context, cards = reply(question, st.session_state['assistant_context'], properties)
                    st.session_state['assistant_context'] = context
                except AssistantUnavailable:
                    cards = []
                    response = 'Не удалось связаться с локальной моделью. Проверьте, запущен ли сервер llama.cpp; подбор по форме продолжит работать.'
                st.session_state['assistant_messages'].append({'role':'assistant','content':response,'cards':cards})
            st.rerun()
        if st.session_state['assistant_messages']:
            if st.button('Начать новый диалог', key='reset_chat'):
                st.session_state['assistant_messages'] = []
                st.session_state['assistant_context'] = {}
                st.rerun()

    st.write('')
    with st.container(border=True):
        st.markdown('<div class="section-kicker">Финансы</div><div class="section-title">Ипотечный калькулятор</div><div class="section-copy">Рассчитайте примерный ежемесячный платёж по своим условиям.</div>', unsafe_allow_html=True)
        with st.form('mortgage_calculator'):
            property_price = st.number_input('Стоимость квартиры, ₽', min_value=1, value=None, placeholder='Например, 15 000 000', step=100000, key='mortgage_price')
            down_col, years_col = st.columns(2)
            with down_col:
                down = st.number_input('Первый взнос, %', min_value=0.0, max_value=99.9, value=20.0, step=1.0, key='mortgage_down')
            with years_col:
                years = st.number_input('Срок, лет', min_value=1, max_value=50, value=20, step=1, key='mortgage_years')
            rate = st.number_input('Ставка банка, % годовых', min_value=0.0, max_value=100.0, value=None, placeholder='Укажите ставку', step=0.1, key='mortgage_rate')
            calculate = st.form_submit_button('Рассчитать ипотеку', type='primary', use_container_width=True)
        if calculate:
            st.session_state.pop('mortgage_result', None)
            st.session_state.pop('mortgage_error', None)
            if property_price is None or rate is None:
                st.session_state['mortgage_error'] = 'Укажите стоимость квартиры и ставку банка.'
            else:
                try:
                    result = calculate_mortgage(property_price, down, rate, years)
                    st.session_state['mortgage_result'] = {'data': result, 'rate': rate}
                except ValueError as exc:
                    st.session_state['mortgage_error'] = str(exc)
        if st.session_state.get('mortgage_error'):
            st.warning(st.session_state['mortgage_error'])
        if st.session_state.get('mortgage_result'):
            saved = st.session_state['mortgage_result']
            result = saved['data']
            st.markdown('<div class="section-kicker" style="margin-top:20px">Ориентировочный платёж</div>', unsafe_allow_html=True)
            st.subheader(f"{result['monthly_payment']:,} ₽ / мес.".replace(',', ' '))
            st.caption(f"Ставка: {saved['rate']:g}% годовых")
            st.caption(f"Кредит: {result['principal']:,} ₽ · Взнос: {result['down_payment']:,} ₽".replace(',', ' '))
            st.caption(f"Проценты за весь срок: {result['total_interest']:,} ₽".replace(',', ' '))
        st.caption('Аннуитетный платёж без страховок и комиссий. Не проверяет право на льготную программу; условия и итоговую стоимость уточняйте в банке.')
