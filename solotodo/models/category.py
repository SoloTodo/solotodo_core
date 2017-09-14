from django.db import models

from metamodel.models import MetaModel
from solotodo.models.category_tier import CategoryTier


class Category(models.Model):
    name = models.CharField(max_length=255, db_index=True, unique=True)
    meta_model = models.OneToOneField(MetaModel, blank=True, null=True)
    tier = models.ForeignKey(CategoryTier, blank=True, null=True)
    slug = models.SlugField(blank=True, null=True)
    storescraper_name = models.CharField(
        max_length=255, db_index=True, blank=True, null=True)
    suggested_alternatives_ordering = models.CharField(
        max_length=255, blank=True, null=True)
    suggested_alternatives_filter = models.CharField(
        max_length=255, blank=True, null=True)
    similar_products_fields = models.CharField(
        max_length=255, null=True, blank=True)
    search_bucket_key_fields = models.CharField(
        max_length=255, null=True, blank=True)
    detail_bucket_key_fields = models.CharField(
        max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'solotodo'
        ordering = ['name']
        permissions = (
            ['view_category', 'Can view the category'],
            ['is_category_staff',
             'Is staff of the category (may also require other permissions)'],
            ['update_category_pricing',
             'Can update the pricing of the category\'s entities'],
        )
