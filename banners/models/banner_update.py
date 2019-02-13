from django.db import models

from solotodo.models import Store


class BannerUpdate(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{} - {}'.format(self.store, self.timestamp)

    class Meta:
        app_label = 'banners'
        ordering = ('store', 'timestamp')
