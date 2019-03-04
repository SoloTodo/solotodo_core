from django.db import models
from django.db.models import F, Q, Sum

from solotodo.models import Store


class BannerAssetQuerySet(models.QuerySet):
    # In this class, every method returns as "self.filter(id__in=xxxx)"
    # where xxxx is the result of another filter (the intended one). This
    # is done because for some reason (still not really understood), applying
    # other filters directly to the first filter generates unexpected results.
    def get_active(self):
        active_assets = self.filter(
            banner__update__store__active_banner_update=F('banner__update'))\
            .distinct()

        return self.filter(id__in=active_assets)

    def get_inactive(self):
        inactive_assets = self.exclude(
            banner__update__store__active_banner_update=F('banner__update'))\
            .distinct()

        return self.filter(id__in=inactive_assets)

    def get_complete(self):
        complete_assets = self.annotate(
            percentage=Sum('contents__percentage')).filter(percentage=100)

        return self.filter(id__in=complete_assets)

    def get_incomplete(self):
        incomplete_assets = self.annotate(
            percentage=Sum('contents__percentage'))\
            .filter(Q(percentage__isnull=True) | ~Q(percentage=100))

        return self.filter(id__in=incomplete_assets)

    def filter_by_user_perms(self, user, permission):
        stores_with_permissions = Store.objects.filter_by_user_perms(
            user, permission)

        filtered_assets = self.filter(
            banner__update__store__in=stores_with_permissions
        ).distinct()

        return self.filter(id__in=filtered_assets)


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

    @property
    def total_percentage(self):
        return self.contents.aggregate(
            Sum('percentage'))['percentage__sum']

    def __str__(self):
        return '{} - {}'.format(self.picture_url, self.creation_date)

    class Meta:
        app_label = 'banners'
        ordering = ('picture_url', 'id')
        permissions = (
            ['is_staff_of_banner_assets', 'Is staff of all banner assets'],
        )
