from django.db import models
from .rs_entity import RSEntity


class RSEntityHistory(models.Model):
    id = models.IntegerField(primary_key=True)
    entity = models.ForeignKey(RSEntity, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    stock = models.IntegerField()
    normal_price = models.DecimalField(decimal_places=2, max_digits=12)
    offer_price = models.DecimalField(decimal_places=2, max_digits=12)
    cell_monthly_payment = models.DecimalField(decimal_places=2, max_digits=12,
                                               null=True)

    class Meta:
        app_label = 'analytics'
        db_table = 'entity_history'
