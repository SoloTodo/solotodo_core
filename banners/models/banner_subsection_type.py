from django.db import models


class BannerSubsectionType(models.Model):
    name = models.CharField(max_length=255)
    storescraper_name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        app_label = 'banners'
