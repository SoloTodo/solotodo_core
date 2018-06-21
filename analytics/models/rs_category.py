from django.db import models


class RSCategory(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)

    class Meta:
        app_label = 'analytics'
        db_table = 'category'
