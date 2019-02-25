from django.db import models
from solotodo.models import Category


class BannerSection(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE,
                                 null=True, blank=True)

    @property
    def name(self):
        return str(self)

    def __str__(self):
        if self.category:
            return self.category.name
        else:
            return 'Home'

    class Meta:
        app_label = 'banners'
