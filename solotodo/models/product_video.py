from django.db import models


class ProductVideo(models.Model):
    youtube_id = models.CharField(max_length=256)
    name = models.CharField(max_length=256)
    conditions = models.CharField(max_length=256)

    def __str__(self):
        return '{} - {}'.format(self.name, self.youtube_id)

    class Meta:
        app_label = 'solotodo'
        ordering = ('-id', )
