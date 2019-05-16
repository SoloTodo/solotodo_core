from django.db import models

from .keyword_search import KeywordSearch


class KeywordSearchUpdate(models.Model):
    IN_PROCESS, SUCCESS, ERROR = [1, 2, 3]

    search = models.ForeignKey(KeywordSearch, on_delete=models.CASCADE)
    creation_date = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(choices=[
        (IN_PROCESS, 'In process'),
        (SUCCESS, 'Success'),
        (ERROR, 'Error'),
    ], default=IN_PROCESS)
    message = models.TextField()

    class Meta:
        app_label = 'keyword_search_positions'
        ordering = ('search',)
