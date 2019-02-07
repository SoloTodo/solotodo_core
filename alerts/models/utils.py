from decimal import Decimal

from solotodo.utils import format_currency


def extract_price(entity_history, pricing_type):
    if entity_history:
        return getattr(entity_history, '{}_price'.format(pricing_type))
    else:
        return None


def calculate_price_delta(previous_price, new_price):
    # Convention for the deltas calculation:
    # None: the product was unavailable, and it's still unavailable
    # -Inf: the product was available, but now is unavailable
    # negative value: the product lowered its price
    # 0: the product maintained its price
    # positive value: the product raised its price
    # +Inf: the product was unavailable, but now is available

    if new_price is None:
        if previous_price is None:
            return None
        else:
            return Decimal('-Inf')
    else:
        if previous_price is None:
            return Decimal('Inf')
        else:
            return new_price - previous_price


def currency_formatter(value):
    return format_currency(value, places=0)
