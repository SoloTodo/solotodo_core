from django.db import models

from .rs_category import RSCategory


class RSProduct(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    creation_date = models.DateTimeField()
    last_updated = models.DateTimeField()
    category = models.ForeignKey(RSCategory, on_delete=models.CASCADE)

    class Meta:
        app_label = 'analytics'
        db_table = 'product'
