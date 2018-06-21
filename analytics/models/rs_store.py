from django.db import models

from .rs_store_type import RSStoreType
from .rs_country import RSCountry


class RSStore(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    country = models.ForeignKey(RSCountry, on_delete=models.CASCADE)
    type = models.ForeignKey(RSStoreType, on_delete=models.CASCADE)

    class Meta:
        app_label = 'analytics'
        db_table = 'store'
