from django.db import models

from solotodo.models.entity import Entity
from solotodo.models.utils import rs_refresh_entries


class EntityHistoryQueryset(models.QuerySet):
    def get_available(self):
        return self.exclude(stock=0)

    def filter_by_user_perms(self, user, permission):
        from solotodo.models import Category, Store

        synth_permissions = {
            'view_entity_history': {
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
            entity__store__in=stores_with_permissions,
            entity__category__in=categories_with_permissions,
        )


class EntityHistory(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(db_index=True)
    stock = models.IntegerField(db_index=True)
    normal_price = models.DecimalField(decimal_places=2, max_digits=12,
                                       db_index=True)
    offer_price = models.DecimalField(decimal_places=2, max_digits=12,
                                      db_index=True)
    cell_monthly_payment = models.DecimalField(decimal_places=2, max_digits=12,
                                               null=True, blank=True,
                                               db_index=True)
    estimated_sales_since_previous_registry = models.PositiveIntegerField(
        default=0)

    objects = EntityHistoryQueryset.as_manager()

    is_available = property(lambda self: self.stock != 0)

    def __str__(self):
        return u'{} - {}'.format(self.entity, self.timestamp)

    @classmethod
    def rs_refresh(cls):
        qs = cls.objects.all()
        rs_refresh_entries(
            qs, 'entity_history', 'timestamp',
            ['id', 'timestamp', 'stock', 'normal_price', 'offer_price',
             'cell_monthly_payment', 'entity_id',
             'estimated_sales_since_previous_registry',
             'is_available'])

    class Meta:
        app_label = 'solotodo'
        ordering = ['entity', 'timestamp']
