import collections
import re
from decimal import Decimal

import requests
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError


def iterable_to_dict(iterable_or_model, field='id'):
    if not isinstance(iterable_or_model, collections.Iterable):
        iterable_or_model = iterable_or_model.objects.all()

    return {getattr(e, field): e for e in iterable_or_model}


# REF: https://stackoverflow.com/questions/4581789/how-do-i-get-user-ip-
# address-in-django
# Yes, I know this can be spoofed, but hopefully it is only used for
# convenience
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def format_currency(value, curr='$', places=2, sep='.', dp=','):
    """Convert Decimal to a money formatted string.

    curr: optional currency symbol before the sign (may be blank)
    sep: optional grouping separator (comma, period, space, or blank)
    dp: decimal point indicator (comma or period)
    only specify as blank when places is zero

    """
    quantized_precision = Decimal(10) ** -places  # 2 places --> '0.01'
    sign, digits, exp = value.quantize(quantized_precision).as_tuple()
    result = []
    digits = list(map(str, digits))
    build, iter_next = result.append, digits.pop

    for i in range(places):
        build(iter_next() if digits else '0')
    if places:
        build(dp)
    if not digits:
        build('0')
    i = 0
    while digits:
        build(iter_next())
        i += 1
        if i == 3 and digits:
            i = 0
            build(sep)
    build(curr)

    return ''.join(reversed(result))


def recursive_dict_search(d, target):
    # Recursively search in the "d" dictionary for the key given by target
    # Returns the value of the dictionary for that key or None if it was
    # not found
    # Only considers dictionary trees, not lists

    if target in d:
        return d[target]

    for k, v in d.items():
        if isinstance(v, dict):
            return recursive_dict_search(v, target)


def get_dotted_dict_value(d, key):
    # Given a dot separated key (e.g. "main_gpu.line_unicode")
    # return the value for the dictionary for its full path
    # (e.g. d['main_gpu']['line_unicode']) or None if some part of the key
    # is not found
    iterator = d

    for key_part in key.split('.'):
        if key_part not in iterator:
            return None
        iterator = iterator[key_part]

    return iterator


def validate_sii_rut(value):
    match = re.match(r'\d{7,8}-[\d|K]$', value)
    if not match:
        raise ValidationError('Invalid RUT format')


def fetch_sec_fields(qr_code):
    zeros = 13 - len(str(qr_code))
    url = 'https://ww6.sec.cl/qr/qr.do?a=prod&i={}{}'.format(zeros * '0', qr_code)
    res = requests.get(url)
    soup = BeautifulSoup(res.text, 'html.parser')
    d = {}
    for label in soup.findAll('strong'):
        key = label.text.strip()[:-1]
        value = label.next.next.next.strip()
        d[key] = value
    return d
