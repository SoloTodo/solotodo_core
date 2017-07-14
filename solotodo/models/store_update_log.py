from django.db import models

from solotodo.models.product_type import ProductType
from solotodo.models.store import Store
from solotodo_try.s3utils import PrivateS3BotoStorage


class StoreUpdateLog(models.Model):
    store = models.ForeignKey(Store)
    product_types = models.ManyToManyField(ProductType)
    status = models.IntegerField(choices=[
        (1, 'Pending'),
        (2, 'In process'),
        (3, 'Sucess'),
        (4, 'Error'),
    ], default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    discovery_url_concurrency = models.IntegerField()
    products_for_url_concurrency = models.IntegerField()
    registry_file = models.FileField(storage=PrivateS3BotoStorage())

    def __str__(self):
        return '{} - {}'.format(self.store, self.creation_date)

    class Meta:
        app_label = 'solotodo'
        ordering = ['store', '-creation_date']
