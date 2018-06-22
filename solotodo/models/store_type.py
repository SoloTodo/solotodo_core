from django.db import models

from solotodo.models.utils import rs_refresh_model


class StoreType(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    @classmethod
    def rs_refresh(cls):
        rs_refresh_model(cls, 'store_type', ['id', 'name'])

    class Meta:
        app_label = 'solotodo'
        ordering = ('name', )
