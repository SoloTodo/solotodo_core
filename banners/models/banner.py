from django.db import models
from django.db.models import F

from banners.models import BannerUpdate, BannerAsset, BannerSubsection
from solotodo.models import Store


class BannerQuerySet(models.QuerySet):
    def get_active(self):
        return self.filter(update__store__active_banner_update=F('update'))

    def get_inactive(self):
        return self.exclude(update__store__active_banner_update=F('update'))

    def filter_by_user_perms(self, user, permission):
        synth_permissions = {
            'view_banner': {
                'store': 'view_store_banners'
            }
        }

        assert permission in synth_permissions

        permissions = synth_permissions[permission]

        stores_with_permissions = Store.objects.filter_by_user_perms(
            user, permissions['store'])

        return self.filter(
            update__store__in=stores_with_permissions
        )


class Banner(models.Model):
    update = models.ForeignKey(BannerUpdate, on_delete=models.CASCADE)
    url = models.URLField()
    asset = models.ForeignKey(BannerAsset, on_delete=models.CASCADE)
    subsection = models.ForeignKey(BannerSubsection, on_delete=models.CASCADE)

    position = models.IntegerField()
    objects = BannerQuerySet.as_manager()

    def __str__(self):
        return '{} - {} - ({}) - {}'.format(self.update, self.asset,
                                            self.subsection, self.position)

    class Meta:
        app_label = 'banners'
        ordering = ('update', 'position', 'asset')
        permissions = (
            ['backend_list_banners', 'Can see banner list in the backend'],
        )
