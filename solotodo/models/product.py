from django.contrib.auth import get_user_model
from django.db import models

from solotodo.models.product_type import ProductType


class Product(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    part_number = models.CharField(max_length=255, db_index=True)
    product_type = models.ForeignKey(ProductType)
    creation_date = models.DateTimeField(db_index=True, auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(get_user_model())

    def __str__(self):
        result = self.name
        if self.part_number:
            result += ' ({})'.format(self.part_number)

        return result

    class Meta:
        app_label = 'solotodo'
