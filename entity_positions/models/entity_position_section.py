from django.db import models

from solotodo.models import Store


class EntityPositionSection(models.Model):
    name = models.CharField(max_length=512)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)

    def __str__(self):
        return '{} - {}'.format(self.store, self.name)

    class Meta:
        app_label = 'entity_positions'
        ordering = ('store', 'name')
