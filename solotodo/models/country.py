from django.db import models
from sorl.thumbnail import ImageField

from solotodo.models.number_format import NumberFormat
from solotodo.models.currency import Currency


class Country(models.Model):
    name = models.CharField(max_length=200)
    iso_code = models.CharField(max_length=2)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    number_format = models.ForeignKey(NumberFormat, on_delete=models.CASCADE)
    flag = ImageField(upload_to='country_flags')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'solotodo'
        ordering = ('name', )
