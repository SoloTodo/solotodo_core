from django.db import models

from microsite.models import MicrositeBrand
from solotodo.models import Product


class MicrositeEntryQuerySet(models.QuerySet):
    def filter_by_user_perms(self, user, permission):
        brands_with_permissions = MicrositeBrand.objects.filter_by_user_perms(
            user, permission)
        return self.filter(brand__in=brands_with_permissions)


class MicrositeEntry(models.Model):
    brand = models.ForeignKey(
        MicrositeBrand, on_delete=models.CASCADE, related_name='entries')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    ordering = models.IntegerField(default=1, null=True, blank=True)
    home_ordering = models.IntegerField(null=True, blank=True)
    sku = models.CharField(max_length=256, null=True, blank=True)
    brand_url = models.URLField(null=True, blank=True)
    title = models.CharField(max_length=256, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    reference_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    custom_attr_1_str = models.CharField(max_length=256, null=True, blank=True)

    objects = MicrositeEntryQuerySet.as_manager()

    def __str__(self):
        return '({}) - {}'.format(self.brand, self.product)

    class Meta:
        app_label = 'microsite'
        ordering = ('product__instance_model__model__category', 'ordering',)
        unique_together = ('brand', 'product')
