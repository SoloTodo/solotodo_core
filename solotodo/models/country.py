from django.conf import settings
from django.db import models
from sorl.thumbnail import ImageField

from solotodo.models.number_format import NumberFormat
from solotodo.models.currency import Currency
from solotodo.models.utils import rs_refresh_model


class Country(models.Model):
    name = models.CharField(max_length=200)
    iso_code = models.CharField(max_length=2)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    number_format = models.ForeignKey(NumberFormat, on_delete=models.CASCADE)
    flag = ImageField(upload_to='country_flags')

    def __str__(self):
        return self.name

    @classmethod
    def get_default(cls):
        return cls.objects.get(pk=settings.CHILE_COUNTRY_ID)

    @classmethod
    def rs_refresh(cls):
        rs_refresh_model(cls, 'country', ['id', 'name'])

    class Meta:
        app_label = 'solotodo'
        ordering = ('name', )
