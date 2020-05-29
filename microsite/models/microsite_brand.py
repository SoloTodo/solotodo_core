from django.db import models


class MicrositeBrand(models.Model):
    name = models.CharField(max_length=512)
    fields = models.CharField(max_length=512)

    class Meta:
        app_label = 'microsite'
