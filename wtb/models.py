from django.db import models

from solotodo.models import Store, Product, Category
from solotodo_try.s3utils import PrivateS3Boto3Storage


class WtbBrand(models.Model):
    name = models.CharField(max_length=100)
    prefered_brand = models.CharField(max_length=100, blank=True, null=True)
    scraper_class = models.CharField(max_length=100, blank=True, null=True)
    stores = models.ManyToManyField(Store)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name', )
        permissions = [
            ('view_wtb_brand', 'Can view the WTB brand'),
            ('backend_view_wtb', 'Display the WTB menu in the backend'),
        ]


class WtbEntity(models.Model):
    name = models.CharField(max_length=255)
    brand = models.ForeignKey(WtbBrand)
    category = models.ForeignKey(Category)
    product = models.ForeignKey(Product, blank=True, null=True)
    key = models.CharField(max_length=255)
    url = models.URLField()
    picture_url = models.URLField()
    creation_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_visible = models.BooleanField(default=True)

    def __str__(self):
        return '{} - {}'.format(self.brand, self.name)

    class Meta:
        ordering = ('brand', 'name')


class WtbBrandUpdateLog(models.Model):
    PENDING, IN_PROCESS, SUCCESS, ERROR = [1, 2, 3, 4]

    brand = models.ForeignKey(WtbBrand)
    status = models.IntegerField(choices=[
        (PENDING, 'Pending'),
        (IN_PROCESS, 'In process'),
        (SUCCESS, 'Success'),
        (ERROR, 'Error'),
    ], default=PENDING)
    creation_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    registry_file = models.FileField(storage=PrivateS3Boto3Storage(),
                                     upload_to='logs/wtb',
                                     null=True, blank=True)

    entity_count = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return '{} - {}'.format(self.brand, self.last_updated)

    class Meta:
        ordering = ('brand', '-last_updated')
