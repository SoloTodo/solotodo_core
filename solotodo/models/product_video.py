from django.db import models


class ProductVideo(models.Model):
    youtube_id = models.CharField(max_length=256)
    name = models.CharField(max_length=256)
    conditions = models.CharField(max_length=256)

    def __str__(self):
        return '{}-{}'.format(self.youtube_id, self.name)

    class Meta:
        app_label = 'solotodo'
        ordering = ('name', )
