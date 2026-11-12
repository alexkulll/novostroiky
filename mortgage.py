from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext


def calculate_mortgage(price, down_payment_percent, annual_rate, years):
    try:
        price = Decimal(str(price))
        down_payment_percent = Decimal(str(down_payment_percent))
        annual_rate = Decimal(str(annual_rate))
        years = Decimal(str(years))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError('Проверьте введённые условия.') from exc
    if not all(x.is_finite() for x in (price, down_payment_percent, annual_rate, years)):
        raise ValueError('Условия должны быть конечными числами.')
    if price <= 0 or not Decimal('0') <= down_payment_percent < Decimal('100'):
        raise ValueError('Стоимость должна быть больше нуля, а первоначальный взнос — меньше 100%.')
    if not Decimal('0') <= annual_rate <= Decimal('100') or not Decimal('1') <= years <= Decimal('50') or years != years.to_integral_value():
        raise ValueError('Укажите ставку от 0 до 100% и срок от 1 до 50 лет.')
    with localcontext() as ctx:
        ctx.prec = 36
        down_payment = price * down_payment_percent / Decimal('100')
        principal = price - down_payment
        months = int(years) * 12
        rate = annual_rate / Decimal('1200')
        payment = principal / months if rate == 0 else principal * rate / (1 - (1 + rate) ** (-months))
        total_interest = payment * months - principal
        rubles = lambda x: int(x.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        return {'down_payment': rubles(down_payment), 'principal': rubles(principal), 'monthly_payment': rubles(payment), 'total_interest': rubles(total_interest)}
