from django.db import models


class EntityState(models.Model):
    name = models.CharField(max_length=30)
    storescraper_name = models.CharField(max_length=30)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'solotodo'
        ordering = ('name', )
