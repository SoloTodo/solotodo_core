from django.db import models

from solotodo.models.currency import Currency


class Country(models.Model):
    name = models.CharField(max_length=200)
    iso_code = models.CharField(max_length=2)
    currency = models.ForeignKey(Currency)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'solotodo'
        ordering = ('name', )
