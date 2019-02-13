from django.db import models

from banners.models import BannerAsset
from solotodo.models import Brand, Category


class BannerAssetContent(models.Model):
    asset = models.ForeignKey(BannerAsset, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    percentage = models.IntegerField()

    def __str__(self):
        return '{} - {} - {} - {}'.format(self.asset, self.brand,
                                          self.category, self.percentage)

    class Meta:
        app_label = 'banners'
        ordering = ('asset', 'brand', 'category')
