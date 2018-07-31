import collections
import hashlib
import json

from decimal import Decimal

import datetime


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


def generate_cache_key(cache_dict):
    return hashlib.sha1(json.dumps(cache_dict).encode('utf-8')).hexdigest()


class Clock(object):
    def __init__(self):
        import time
        self.time = time.monotonic()

    def tick(self, label):
        import time
        new_time = time.monotonic()
        print('{}: {}'.format(label, new_time - self.time))
        self.time = new_time


# REF https://stackoverflow.com/questions/304256/whats-the-best-way-to-
# find-the-inverse-of-datetime-isocalendar
def iso_year_start(iso_year):
    "The gregorian calendar date of the first day of the given ISO year"
    fourth_jan = datetime.datetime(iso_year, 1, 4)
    delta = datetime.timedelta(fourth_jan.isoweekday()-1)
    return fourth_jan - delta


def iso_to_gregorian(iso_year, iso_week, iso_day):
    "Gregorian calendar date for the given ISO year, week and day"
    year_start = iso_year_start(iso_year)
    return year_start + datetime.timedelta(days=iso_day-1, weeks=iso_week-1)


def convert_hometheater_to_stereosystem(product):
    from metamodel.models import MetaModel, InstanceModel
    from metamodel.signals import instance_model_saved
    from django.db.models import signals
    from solotodo.models import delete_product_from_es, \
        create_or_update_product

    signals.pre_delete.disconnect(delete_product_from_es, sender=InstanceModel)
    instance_model_saved.disconnect(create_or_update_product)

    home_theater = product.instance_model

    stereo_system_model = MetaModel.objects.get(pk=363)
    stereo_system = InstanceModel(model=stereo_system_model)
    stereo_system.save(initial=True)

    stereo_system.name = home_theater.name
    stereo_system.energy_efficiency_cl = home_theater.energy_efficiency_cl
    stereo_system.standby_monthly_consumption_cl = \
        home_theater.standby_monthly_consumption_cl or 0
    stereo_system.picture = home_theater.picture

    # Brand
    stereo_system_brand_model = MetaModel.objects.get(pk=364)
    stereo_system_brand = stereo_system_brand_model.instancemodel_set.get(
        unicode_representation=home_theater.brand.name)
    stereo_system.brand = stereo_system_brand

    # Category
    stereo_system_category_model = MetaModel.objects.get(pk=365)
    stereo_system_category = \
        stereo_system_category_model.instancemodel_set.get(
            unicode_representation=home_theater.category.name)
    stereo_system.category = stereo_system_category

    # RMS Power
    stereo_system_rms_power_model = MetaModel.objects.get(pk=366)
    stereo_system_rms_power = \
        stereo_system_rms_power_model.instancemodel_set.get(
            unicode_representation=str(home_theater.audio_power))
    stereo_system.rms_power = stereo_system_rms_power

    # PMPO Power
    stereo_system_unknown_pmpo_power = InstanceModel.objects.get(pk=372405)
    stereo_system.pmpo_power = stereo_system_unknown_pmpo_power

    # OpticalDiskFormat
    stereo_system_optical_drive_model = MetaModel.objects.get(pk=368)
    stereo_system_optical_drive = \
        stereo_system_optical_drive_model.instancemodel_set.get(
            unicode_representation=home_theater.optical_disk_format.name)
    stereo_system.optical_drive = stereo_system_optical_drive

    stereo_system.has_ipod_connector = home_theater.has_iphone_dock
    stereo_system.has_android_connector = home_theater.has_android_dock
    stereo_system.has_fm_radio = home_theater.has_fm_radio
    stereo_system.has_bluetooth = home_theater.has_bluetooth or False
    stereo_system.has_wifi = home_theater.has_wifi
    stereo_system.speaker_format = home_theater.speaker_format
    stereo_system.ports = home_theater.ports

    # USB Ports
    usb_1_port = InstanceModel.objects.get(pk=388349)
    if usb_1_port in home_theater.ports:
        usb_ports = 1
    else:
        usb_ports = 0
    stereo_system.usb_ports = usb_ports

    stereo_system.save(creator_id=53168)

    product.instance_model = stereo_system
    product.save()
    home_theater.delete()

    return product
