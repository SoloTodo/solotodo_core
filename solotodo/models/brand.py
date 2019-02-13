from django.db import models


class Brand(models.Model):
    name = models.CharField(max_length=255, db_index=True, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'solotodo'
        ordering = ('name',)
