from django.db import models
from guardian.shortcuts import get_objects_for_user

from solotodo.models import Product


class MicrositeBrandQuerySet(models.QuerySet):
    def filter_by_user_perms(self, user, permission):
        return get_objects_for_user(user, permission, self)


class MicrositeBrand(models.Model):
    name = models.CharField(max_length=512)
    fields = models.CharField(max_length=512)

    objects = MicrositeBrandQuerySet.as_manager()

    def create_entry_from_product(self, product_id):
        from microsite.models import MicrositeEntry
        product = Product.objects.get(id=product_id)
        MicrositeEntry.objects.create(brand=self, product=product)

    class Meta:
        app_label = 'microsite'
        permissions = (
            ['view_microsite_brand', 'Can see the brand'],
            ['change_microsite_brand', 'Can edit brand entries'],
            ['pricing_view_microsite', 'Can see microsite view on pricing'],
        )
