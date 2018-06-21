from django.db import models

from .rs_category import RSCategory
from .rs_product import RSProduct
from .rs_store import RSStore
from .rs_currency import RSCurrency


class RSEntity(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    store = models.ForeignKey(RSStore, on_delete=models.CASCADE)
    category = models.ForeignKey(RSCategory, on_delete=models.CASCADE)
    currency = models.ForeignKey(RSCurrency, on_delete=models.CASCADE)
    condition = models.CharField(max_length=100)
    product = models.ForeignKey(RSProduct, on_delete=models.CASCADE, null=True)
    cell_plan = models.ForeignKey(RSProduct, on_delete=models.CASCADE,
                                  null=True, related_name='+')
    active_registry = models.OneToOneField('RSEntityHistory',
                                           on_delete=models.CASCADE,
                                           related_name='+',
                                           null=True)
    part_number = models.CharField(max_length=50, null=True)
    sku = models.CharField(max_length=50, null=True)
    ean = models.CharField(max_length=15, null=True)
    key = models.CharField(max_length=256)
    url = models.URLField(max_length=512)
    creation_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'analytics'
        db_table = 'entity'
