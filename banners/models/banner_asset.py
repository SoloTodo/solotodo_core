from django.db import models

from solotodo.models import Store


class BannerAssetQuerySet(models.QuerySet):
    def filter_by_user_perms(self, user, permission):
        stores_with_permissions = Store.objects.filter_by_user_perms(
            user, permission)

        return self.filter(
            banner__update__store__in=stores_with_permissions
        ).distinct()


class BannerAsset(models.Model):
    key = models.CharField(max_length=255, unique=True, default="")
    picture_url = models.URLField()
    creation_date = models.DateTimeField(auto_now_add=True)
    objects = BannerAssetQuerySet.as_manager()

    def __str__(self):
        return '{} - {}'.format(self.picture_url, self.creation_date)

    class Meta:
        app_label = 'banners'
        ordering = ('picture_url',)
