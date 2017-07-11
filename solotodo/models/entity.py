from django.db import models

from solotodo.models.currency import Currency
from solotodo.models.product_type import ProductType
from solotodo.models.store import Store


class Entity(models.Model):
    store = models.ForeignKey(Store)
    product_type = models.ForeignKey(ProductType)
    scraped_product_type = models.ForeignKey(ProductType, related_name='+')
    currency = models.ForeignKey(Currency)
    active_registry = models.OneToOneField('EntityHistory', related_name='+')

    name = models.CharField(max_length=256, db_index=True)
    cell_plan_name = models.CharField(max_length=50, null=True,
                                      blank=True, db_index=True)
    part_number = models.CharField(max_length=50, null=True, blank=True,
                                   db_index=True)
    sku = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    key = models.CharField(max_length=256, db_index=True)
    url = models.URLField(max_length=512, unique=True, db_index=True)
    discovery_url = models.URLField(max_length=512, unique=True, db_index=True)
    description = models.TextField(db_index=True)
    is_visible = models.BooleanField(default=True)
    latest_association_date = models.DateTimeField(null=True, blank=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        result = '{} - {}'.format(self.store, self.name)
        if self.cell_plan_name:
            result += ' / {}'.format(self.cell_plan_name)
        result += ' ({})'.format(self.product_type)

        return result

    class Meta:
        app_label = 'solotodo'
        unique_together = ('store', 'key')
