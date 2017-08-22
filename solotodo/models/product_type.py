from django.db import models

from metamodel.models import MetaModel
from solotodo.models.product_type_tier import ProductTypeTier


class ProductType(models.Model):
    name = models.CharField(max_length=255, db_index=True, unique=True)
    meta_model = models.OneToOneField(MetaModel, blank=True, null=True)
    tier = models.ForeignKey(ProductTypeTier, blank=True, null=True)
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
            ['view_product_type_entities',
             'Can view entities associated to this product type'],
            ['view_product_type_products',
             'Can view products associated to this product type'],
            ['associate_product_type_entities',
             'Can associate product type entities'],
        )
