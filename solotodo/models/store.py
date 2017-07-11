from django.db import models


class Store(models.Model):
    name = models.CharField(max_length=255, db_index=True, unique=True)
    is_active = models.BooleanField(default=True)
    storescraper_class = models.CharField(max_length=255, db_index=True)
    storescraper_extra_args = models.CharField(max_length=255, null=True,
                                               blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        app_label = 'solotodo'
