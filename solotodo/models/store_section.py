from django.db import models
from django.db.models import Q

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

    def get_pending(self):
        return self.filter(parent__isnull=True, is_root=False)

    def get_done(self):
        return self.filter(Q(parent__isnull=False) | Q(is_root=True))


class StoreSection(models.Model):
    name = models.CharField(max_length=512)
    store = models.ForeignKey(Store, on_delete=models.CASCADE,
                              related_name='sections')
    parent = models.ForeignKey('self', on_delete=models.CASCADE,
                               related_name='children', null=True, blank=True)
    is_root = models.BooleanField(default=False)

    objects = StoreSectionQuerySet.as_manager()

    def __str__(self):
        if self.parent:
            return '{} > {}'.format(self.parent, self.name)
        else:
            return '{} - {}'.format(self.store, self.name)

    class Meta:
        app_label = 'solotodo'
        ordering = ('store', 'name')
        unique_together = [('store', 'name')]
