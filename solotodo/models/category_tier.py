from django.db import models


class CategoryTier(models.Model):
    name = models.CharField(max_length=255)
    creation_payment_amount = models.DecimalField(max_digits=5,
                                                  decimal_places=0)
    default_currency_code = 'CLP'

    def __str__(self):
        return '{} ({})'.format(self.name, self.creation_payment_amount)

    class Meta:
        ordering = ['name']
        app_label = 'solotodo'
