from django.contrib.auth import get_user_model
from django.db import models

from solotodo.models import Product


class Budget(models.Model):
    name = models.CharField(max_length=255)
    is_public = models.BooleanField(default=False)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE,
                             related_name='budgets')
    creation_date = models.DateTimeField(auto_now_add=True)
    products_pool = models.ManyToManyField(Product, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'hardware'
        ordering = ['-pk']
