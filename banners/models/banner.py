from django.db import models

from banners.models import BannerUpdate, BannerAsset


class Banner(models.Model):
    update = models.ForeignKey(BannerUpdate, on_delete=models.CASCADE)
    asset = models.ForeignKey(BannerAsset, on_delete=models.CASCADE)
    position = models.IntegerField()

    def __str__(self):
        return '{} - {}'.format(self.update, self.position)

    class Meta:
        app_label = 'banners'
        ordering = ('update', 'asset')
