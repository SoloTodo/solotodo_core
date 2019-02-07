from django.db import models

from .alert import Alert
from solotodo.models import EntityHistory


class AlertNotification(models.Model):
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE,
                              related_name='notifications')
    previous_normal_price_registry = models.ForeignKey(
        EntityHistory, blank=True, null=True, on_delete=models.CASCADE,
        related_name='+')
    previous_offer_price_registry = models.ForeignKey(
        EntityHistory, blank=True, null=True, on_delete=models.CASCADE,
        related_name='+')
    creation_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{} - {}'.format(self.alert, self.creation_date)

    class Meta:
        app_label = 'alerts'
        ordering = ('-creation_date', )
