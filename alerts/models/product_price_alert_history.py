from django.db import models

from alerts.models import ProductPriceAlert


class ProductPriceAlertHistory(models.Model):
    alert = models.ForeignKey(
        ProductPriceAlert,
        on_delete=models.CASCADE,
        related_name='histories')

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'alerts'
        ordering = ('-timestamp',)
