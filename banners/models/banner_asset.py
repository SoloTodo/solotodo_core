from django.db import models


class BannerAsset(models.Model):
    picture_url = models.URLField()

    def __str__(self):
        return '{}'.format(self.picture_url)

    class Meta:
        app_label = 'banners'
        ordering = ('picture_url',)
