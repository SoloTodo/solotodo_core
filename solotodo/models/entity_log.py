from django.contrib.auth import get_user_model
from django.db import models

from gtin_fields import fields as gtin_fields

from .entity import Entity
from .category import Category
from .currency import Currency
from .product import Product


class EntityLog(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    creation_date = models.DateTimeField(auto_now_add=True)

    # Actual data change fields
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    scraped_category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='+')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    condition = models.URLField(choices=[
        ('https://schema.org/DamagedCondition', 'Damaged'),
        ('https://schema.org/NewCondition', 'New'),
        ('https://schema.org/RefurbishedCondition', 'Refurbished'),
        ('https://schema.org/UsedCondition', 'Used')]
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    cell_plan = models.ForeignKey(Product, on_delete=models.CASCADE, null=True,
                                  related_name='+')
    name = models.CharField(max_length=256)
    cell_plan_name = models.CharField(max_length=60, null=True)
    part_number = models.CharField(max_length=50, null=True)
    sku = models.CharField(max_length=50, null=True)
    ean = gtin_fields.EAN13Field(null=True, blank=True)
    url = models.URLField(max_length=512)
    discovery_url = models.URLField(max_length=512)
    picture_urls = models.TextField(null=True)
    description = models.TextField(null=True)
    is_visible = models.BooleanField()

    DATA_FIELDS = [
        'category',
        'scraped_category',
        'currency',
        'condition',
        'product',
        'cell_plan',
        'name',
        'cell_plan_name',
        'part_number',
        'sku',
        'ean',
        'url',
        'discovery_url',
        'picture_urls',
        'description',
        'is_visible',
    ]

    def __str__(self):
        return '{} - {} - {}'.format(self.entity, self.creation_date,
                                     self.user)

    class Meta:
        app_label = 'solotodo'
        ordering = ('entity', '-creation_date')
