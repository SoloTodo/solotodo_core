from django.db import models

from .store import Store


class StoreSectionQuerySet(models.QuerySet):
    def filter_by_user_perms(self, user, permission):
        synth_permissions = {
            'view_store_section': {
                'store': 'view_store_entity_positions',
            }
        }

        assert permission in synth_permissions

        permission = synth_permissions[permission]

        stores_with_permissions = Store.objects.filter_by_user_perms(
            user, permission['store'])

        return self.filter(store__in=stores_with_permissions)


class StoreSection(models.Model):
    name = models.CharField(max_length=512)
    store = models.ForeignKey(Store, on_delete=models.CASCADE,
                              related_name='sections')

    objects = StoreSectionQuerySet.as_manager()

    def __str__(self):
        return '{} - {}'.format(self.store, self.name)

    class Meta:
        app_label = 'solotodo'
        ordering = ('store', 'name')
        unique_together = [('store', 'name')]
