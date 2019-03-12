from django.db import models
from django.core.exceptions import ValidationError

from solotodo.models import Product


class ProductListEntry(models.Model):
    product_list = models.ForeignKey('product_lists.ProductList',
                                     on_delete=models.CASCADE,
                                     related_name='entries')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    ordering = models.IntegerField()

    def __str__(self):
        return '{} - {}'.format(self.product_list, self.product)

    def clean(self):
        if self.product.category != self.product_list.category:
            raise ValidationError('Product category does not match '
                                  'Product List category')

    def save(self, *args, **kwargs):
        self.clean()
        super(ProductListEntry, self).save(*args, ** kwargs)

    class Meta:
        app_label = 'product_lists'
        unique_together = ('product_list', 'product')
        ordering = ('product_list', 'ordering')
