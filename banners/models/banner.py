from django.db import models
from django.db.models import F

from banners.models import BannerUpdate, BannerAsset, BannerAssetContent, \
    BannerSubsection
from solotodo.models import Store


class BannerQuerySet(models.QuerySet):
    def get_active(self):
        return self.filter(update__store__active_banner_update=F('update'))

    def get_inactive(self):
        return self.exclude(update__store__active_banner_update=F('update'))

    def get_contents_data(self, brands, categories):
        contents_data = []
        contents = BannerAssetContent.objects.filter(asset__banner__in=self)

        if brands:
            contents = contents.filter(brand__in=brands)
        if categories:
            contents = contents.filter(category__in=categories)

        contents = contents.distinct()

        for banner in self:
            for content in banner.asset.contents.all():
                if content in contents:
                    contents_data.append({
                        'banner': banner,
                        'content': content})

        return contents_data

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
    destination_urls = models.CharField(max_length=512)
    asset = models.ForeignKey(BannerAsset, on_delete=models.CASCADE)
    subsection = models.ForeignKey(BannerSubsection, on_delete=models.CASCADE)

    position = models.IntegerField()
    objects = BannerQuerySet.as_manager()

    @property
    def destination_url_list(self):
        if self.destination_urls:
            return self.destination_urls.split(',')
        else:
            return []

    def __str__(self):
        return '{} - {} - ({}) - {}'.format(self.update, self.asset,
                                            self.subsection, self.position)

    class Meta:
        app_label = 'banners'
        ordering = ('update', 'position', 'asset')
        permissions = (
            ['backend_list_banners', 'Can see banner list in the backend'],
        )
