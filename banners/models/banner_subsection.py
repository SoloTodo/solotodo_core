from django.db import models

from banners.models import BannerSection, BannerSubsectionType


class BannerSubsection(models.Model):
    name = models.CharField(max_length=255)
    section = models.ForeignKey(BannerSection, on_delete=models.CASCADE)
    type = models.ForeignKey(BannerSubsectionType, on_delete=models.CASCADE)

    def __str__(self):
        return '{} > {} ({})'.format(self.section, self.name, self.type)

    class Meta:
        ordering = ('section', 'name')
        app_label = 'banners'
