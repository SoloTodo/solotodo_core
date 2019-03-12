from django.db import models
from django.contrib.auth import get_user_model

from solotodo.models import Product, Category
from .product_list_entry import ProductListEntry


class ProductList(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE,
                             related_name='product_lists')
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, through=ProductListEntry)

    creation_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '{} - {} - {}'.format(self.name, self.user, self.category)

    class Meta:
        app_label = 'product_lists'
        ordering = ('-id',)
        permissions = (
            ['backend_list_product_lists',
             'Can see product lists in the backend'],
        )
