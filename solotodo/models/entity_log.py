from django.contrib.auth import get_user_model
from django.db import models

from .bundle import Bundle
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
    scraped_condition = models.URLField(choices=[
        ('https://schema.org/DamagedCondition', 'Damaged'),
        ('https://schema.org/NewCondition', 'New'),
        ('https://schema.org/RefurbishedCondition', 'Refurbished'),
        ('https://schema.org/UsedCondition', 'Used')]
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    cell_plan = models.ForeignKey(Product, on_delete=models.CASCADE, null=True,
                                  related_name='+')
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=256)
    cell_plan_name = models.CharField(max_length=60, null=True)
    part_number = models.CharField(max_length=50, null=True)
    sku = models.CharField(max_length=50, null=True)
    ean = models.CharField(max_length=50, null=True, blank=True)
    url = models.URLField(max_length=512)
    discovery_url = models.URLField(max_length=512)
    picture_urls = models.TextField(null=True)
    description = models.TextField(null=True)
    is_visible = models.BooleanField()
    video_urls = models.TextField(blank=True, null=True)
    flixmedia_id = models.CharField(max_length=256, blank=True, null=True)
    review_count = models.IntegerField(blank=True, null=True)
    review_avg_score = models.FloatField(blank=True, null=True)
    has_virtual_assistant = models.BooleanField(null=True, blank=True)

    DATA_FIELDS = [
        'category',
        'scraped_category',
        'currency',
        'condition',
        'scraped_condition',
        'product',
        'cell_plan',
        'bundle',
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
        'video_urls',
        'flixmedia_id',
        'review_count',
        'review_avg_score',
        'has_virtual_assistant',
    ]

    def __str__(self):
        return '{} - {} - {}'.format(self.entity, self.creation_date,
                                     self.user)

    class Meta:
        app_label = 'solotodo'
        ordering = ('entity', '-creation_date')
