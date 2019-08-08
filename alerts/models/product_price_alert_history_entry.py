from django.db import models

from alerts.models import ProductPriceAlertHistory
from solotodo.models import Entity, EntityHistory


class ProductPriceAlertHistoryEntry(models.Model):
    history = models.ForeignKey(
        ProductPriceAlertHistory,
        on_delete=models.CASCADE,
        related_name='entries')

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    normal_price_registry = models.ForeignKey(
        EntityHistory, blank=True, null=True,
        on_delete=models.CASCADE, related_name='+')
    offer_price_registry = models.ForeignKey(
        EntityHistory, blank=True, null=True,
        on_delete=models.CASCADE, related_name='+')

    class Meta:
        app_label = 'alerts'
