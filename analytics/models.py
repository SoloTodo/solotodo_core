from django.db import models


class AnalyticsEntity(models.Model):
    id = models.IntegerField(primary_key=True)
    product = models.CharField(max_length=255)
    category = models.CharField(max_length=50)
    last_updated = models.DateTimeField()


    class Meta:
        app_label = 'analytics'
        db_table = 'entity'
        ordering = ['last_updated']

