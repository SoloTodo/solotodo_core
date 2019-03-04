from django.db import models
from django.db.models import F

from solotodo.models import Store


class BannerUpdateQuerySet(models.QuerySet):
    def get_active(self):
        return self.filter(store__active_banner_update=F('id'))

    def get_inactive(self):
        return self.exclude(store__active_banner_update=F('id'))

    def filter_by_user_perms(self, user, permission):
        synth_permissions = {
            'view_banner_update': {
                'store': 'view_store_banners'
            }
        }

        assert permission in synth_permissions

        permissions = synth_permissions[permission]

        stores_with_permissions = Store.objects.filter_by_user_perms(
            user, permissions['store'])

        return self.filter(
            store__in=stores_with_permissions
        )


class BannerUpdate(models.Model):
    IN_PROCESS, SUCCESS, ERROR = [1, 2, 3]

    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(choices=[
        (IN_PROCESS, 'In process'),
        (SUCCESS, 'Success'),
        (ERROR, 'Error'),
    ], default=IN_PROCESS)
    status_message = models.CharField(max_length=255, blank=True, null=True)

    objects = BannerUpdateQuerySet.as_manager()

    @property
    def is_active(self):
        return self.store.active_banner_update == self

    def __str__(self):
        return '{} - {}'.format(self.store, self.timestamp)

    class Meta:
        app_label = 'banners'
        ordering = ('store', 'timestamp')
