from django.db import models


class RSCurrency(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    iso_code = models.CharField(max_length=10)
    exchange_rate = models.DecimalField(decimal_places=2, max_digits=8)
    exchange_rate_last_updated = models.DateTimeField()

    class Meta:
        app_label = 'analytics'
        db_table = 'currency'
