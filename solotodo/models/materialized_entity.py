from django.db import models

from .product import Product
from .store import Store
from .currency import Currency
from .category import Category
from .store_type import StoreType
from .country import Country


class MaterializedEntityQueryset(models.QuerySet):
    def filter_by_user_perms(self, user, permission):
        synth_permissions = {
            'view_materialized_entity': {
                'store': 'view_store',
                'category': 'view_category',
            }
        }

        assert permission in synth_permissions

        permissions = synth_permissions[permission]

        stores_with_permissions = Store.objects.filter_by_user_perms(
            user, permissions['store'])
        categories_with_permissions = Category.objects.filter_by_user_perms(
            user, permissions['category'])

        return self.filter(
            store__in=stores_with_permissions,
            category__in=categories_with_permissions,
        )


class MaterializedEntity(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    store_type = models.ForeignKey(StoreType, on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    normal_price = models.DecimalField(decimal_places=2, max_digits=12)
    normal_price_usd = models.DecimalField(decimal_places=2, max_digits=12)
    offer_price = models.DecimalField(decimal_places=2, max_digits=12)
    offer_price_usd = models.DecimalField(decimal_places=2, max_digits=12)
    reference_normal_price = models.DecimalField(decimal_places=2,
                                                 max_digits=12, null=True)
    reference_offer_price = models.DecimalField(decimal_places=2,
                                                max_digits=12, null=True)
    leads = models.IntegerField()

    objects = MaterializedEntityQueryset.as_manager()

    def __str__(self):
        return '{} - {}: {} {} / {}'.format(
            self.product, self.store, self.currency.iso_code,
            self.normal_price, self.offer_price)

    class Meta:
        managed = False
        db_table = 'solotodo_materializedentity'
        app_label = 'solotodo'
