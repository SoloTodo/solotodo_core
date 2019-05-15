from django.db import models

from .keyword_search import KeywordSearch


class KeywordSearchUpdate(models.Model):
    search = models.ForeignKey(KeywordSearch, on_delete=models.CASCADE)
    creation_date = models.DateTimeField()
    status = models.CharField(max_length=512)
    message = models.CharField(max_length=512)

    class Meta:
        app_label = 'keyword_search_positions'
        ordering = ('search',)
