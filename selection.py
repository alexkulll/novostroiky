import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / 'data' / 'complexes.csv'
MIN_AREA = Decimal('10')
MAX_AREA = Decimal('1000')

def load_complexes(path=DATA_PATH):
    with Path(path).open(encoding='utf-8-sig', newline='') as file:
        rows = list(csv.DictReader(file))
    required = {'id', 'city', 'complex_name', 'price_per_sqm', 'latitude', 'longitude', 'photo_path'}
    if not rows or not required.issubset(rows[0]):
        raise ValueError('Не удалось прочитать обязательные поля таблицы ЖК.')
    identifiers = set()
    for row in rows:
        if not row['id'] or row['id'] in identifiers:
            raise ValueError('В таблице найден пустой или повторяющийся ID ЖК.')
        identifiers.add(row['id'])
        row['price_per_sqm'] = int(row['price_per_sqm'])
        if row['price_per_sqm'] <= 0:
            raise ValueError('Цена за м² должна быть положительной.')
    return rows

def select_complexes(rows, city, budget, area, limit=3):
    try:
        budget, area = Decimal(str(budget)), Decimal(str(area))
        if not budget.is_finite() or not area.is_finite() or budget <= 0 or area <= 0:
            raise ValueError('Бюджет и площадь должны быть больше нуля.')
    except (InvalidOperation, TypeError) as exc:
        raise ValueError('Проверьте бюджет и площадь.') from exc
    if not MIN_AREA <= area <= MAX_AREA:
        raise ValueError('Введите площадь от 10 до 1000 м².')
    result = []
    for row in rows:
        if row['city'] != city:
            continue
        estimate = (Decimal(row['price_per_sqm']) * area).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        if estimate <= budget:
            result.append({**row, 'estimated_price': int(estimate)})
    return sorted(result, key=lambda x: (x['estimated_price'], x['complex_name']))[:limit]
