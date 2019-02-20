from django.db import models
from django.db.models import F, Q, Sum

from solotodo.models import Store


class BannerAssetQuerySet(models.QuerySet):
    def get_active(self):
        return self.filter(
            banner__update__store__active_banner_update=F('banner__update'))\
            .distinct()

    def get_inactive(self):
        return self.exclude(
            banner__update__store__active_banner_update=F('banner__update'))\
            .distinct()

    def get_complete(self):
        return self.annotate(percentage=Sum('contents__percentage'))\
            .filter(percentage=100)

    def get_incomplete(self):
        return self.annotate(percentage=Sum('contents__percentage'))\
            .filter(Q(percentage__isnull=True) | ~Q(percentage=100))

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

    @property
    def is_active(self):
        return bool(self.banner_set.filter(
            update__store__active_banner_update=F('update')))

    @property
    def is_complete(self):
        return self.contents.aggregate(
            Sum('percentage'))['percentage__sum'] == 100

    def __str__(self):
        return '{} - {}'.format(self.picture_url, self.creation_date)

    class Meta:
        app_label = 'banners'
        ordering = ('picture_url',)
        permissions = (
            ['is_staff_of_banner_assets', 'Is staff of all banner assets'],
        )
