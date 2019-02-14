from django.db import models
from django.db.models import F

from solotodo.models import Store


class BannerUpdateQuerySet(models.QuerySet):
    def get_active(self):
        return self.filter(store__active_banner_update=F('id'))

    def get_inactive(self):
        return self.exclude(store__active_banner_update=F('id'))

    def filter_by_user_perms(self, user, permission):
        stores_with_permissions = Store.objects.filter_by_user_perms(
            user, permission)

        return self.filter(
            store__in=stores_with_permissions
        )


class BannerUpdate(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    objects = BannerUpdateQuerySet.as_manager()

    def __str__(self):
        return '{} - {}'.format(self.store, self.timestamp)

    class Meta:
        app_label = 'banners'
        ordering = ('store', 'timestamp')
