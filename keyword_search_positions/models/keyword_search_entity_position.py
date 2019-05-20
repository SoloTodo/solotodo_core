from django.db import models

from .keyword_search_update import KeywordSearchUpdate
from solotodo.models import Entity


class KeywordSearchEntityPosition(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    update = models.ForeignKey(KeywordSearchUpdate, on_delete=models.CASCADE,
                               related_name='positions')
    value = models.IntegerField()

    def __str__(self):
        return '{} - {} - {}'.format(self.update, self.entity, self.value)

    class Meta:
        app_label = 'keyword_search_positions'
        ordering = ('update', 'value')
