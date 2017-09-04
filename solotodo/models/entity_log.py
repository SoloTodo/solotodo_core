from django.contrib.auth import get_user_model
from django.db import models

from .entity import Entity
from .category import Category
from .entity_state import EntityState
from .currency import Currency
from .product import Product


class EntityLog(models.Model):
    entity = models.ForeignKey(Entity)
    user = models.ForeignKey(get_user_model())
    creation_date = models.DateTimeField(auto_now_add=True)

    # Actual data change fields
    category = models.ForeignKey(Category)
    scraped_category = models.ForeignKey(
        Category, related_name='+')
    currency = models.ForeignKey(Currency)
    state = models.ForeignKey(EntityState)
    product = models.ForeignKey(Product, null=True)
    cell_plan = models.ForeignKey(Product, null=True, related_name='+')
    name = models.CharField(max_length=256)
    cell_plan_name = models.CharField(max_length=50, null=True)
    part_number = models.CharField(max_length=50, null=True)
    sku = models.CharField(max_length=50, null=True)
    url = models.URLField(max_length=512)
    discovery_url = models.URLField(max_length=512)
    picture_url = models.URLField(max_length=512, null=True)
    description = models.TextField(null=True)
    is_visible = models.BooleanField()

    DATA_FIELDS = [
        'category',
        'scraped_category',
        'currency',
        'state',
        'product',
        'cell_plan',
        'name',
        'cell_plan_name',
        'part_number',
        'sku',
        'url',
        'discovery_url',
        'picture_url',
        'description',
        'is_visible',
    ]

    def __str__(self):
        return '{} - {} - {}'.format(self.entity, self.creation_date,
                                     self.user)

    class Meta:
        app_label = 'solotodo'
        ordering = ['-pk']
