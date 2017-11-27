from decimal import Decimal
import json
from urllib import request

from django.conf import settings
from django.db import models
from django.utils import timezone


class Currency(models.Model):
    name = models.CharField(max_length=255)
    iso_code = models.CharField(max_length=10)
    decimal_places = models.IntegerField()
    prefix = models.CharField(max_length=10, default='$')
    exchange_rate = models.DecimalField(decimal_places=2, max_digits=8)
    exchange_rate_last_updated = models.DateTimeField()

    def __str__(self):
        return self.name

    def convert_from(self, value, original_currency):
        if self == original_currency:
            return value

        converted_value = value * self.exchange_rate / \
            original_currency.exchange_rate
        precision = Decimal(str(10 ** -self.decimal_places))

        return converted_value.quantize(precision)

    @classmethod
    def get_default(cls):
        return cls.objects.get(pk=settings.DEFAULT_CURRENCY)

    @classmethod
    def update_exchange_rates(cls):
        currencies = cls.objects.all()

        currency_codes = ','.join([c.iso_code for c in currencies])
        url = 'http://apilayer.net/api/live?access_key={}&currencies={}' \
              ''.format(settings.CURRENCYLAYER_API_ACCESS_KEY, currency_codes)
        xr_data = json.loads(request.urlopen(url).read().decode(
            'utf-8'))['quotes']

        for currency in currencies:
            xr_key = 'USD' + currency.iso_code
            exchange_rate = xr_data[xr_key]
            currency.exchange_rate = exchange_rate
            currency.exchange_rate_last_updated = timezone.now()
            currency.save()

    class Meta:
        app_label = 'solotodo'
        ordering = ['name']
