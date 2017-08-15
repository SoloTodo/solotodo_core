import collections

from django.contrib.auth import get_user_model
from django.db import models

from metamodel.models import InstanceModel


class ProductQuerySet(models.QuerySet):
    def filter_product_type(self, product_type):
        lookup = 'instance_model__model__producttype'
        if isinstance(product_type, collections.Iterable):
            lookup += '__in'

        return self.filter(**{lookup: product_type})


class Product(models.Model):
    instance_model = models.ForeignKey(InstanceModel)
    creation_date = models.DateTimeField(db_index=True, auto_now_add=True)
    creator = models.ForeignKey(get_user_model())

    objects = ProductQuerySet.as_manager()

    product_type = property(lambda self: self.instance_model.model.producttype)

    def __str__(self):
        return str(self.instance_model)

    class Meta:
        app_label = 'solotodo'
        ordering = ('instance_model', )
