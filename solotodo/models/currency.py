from decimal import Decimal
import json
from urllib import request
from django.db import models
from django.utils import timezone
from storescraper.utils import format_currency


class Currency(models.Model):
    name = models.CharField(max_length=255)
    iso_code = models.CharField(max_length=10)
    decimal_places = models.IntegerField()
    prefix = models.CharField(max_length=10, default='$')
    exchange_rate = models.DecimalField(decimal_places=2, max_digits=8)
    exchange_rate_last_updated = models.DateTimeField()

    def __str__(self):
        return self.name

    def update_exchange_rate(self):
        url = 'https://query.yahooapis.com/v1/public/yql' \
              '?q=select%20*%20from%20yahoo.finance.xchange%20where%20pair' \
              '%20in%20(%22USD{0}%22)&format=json&diagnostics=true&env=store' \
              '%3A%2F%2Fdatatables.org%2Falltableswithkeys&callback='.format(
                  self.iso_code
              )
        xr_data = json.loads(request.urlopen(url).read().decode('utf-8'))

        exchange_rate = xr_data['query']['results']['rate']['Rate']

        self.exchange_rate = Decimal(exchange_rate)
        self.exchange_rate_last_updated = timezone.now()
        self.save()

    class Meta:
        app_label = 'solotodo'
        ordering = ['name']
