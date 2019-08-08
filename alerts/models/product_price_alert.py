from django.db import models
from django.contrib.auth import get_user_model

from solotodo.models import Product, Store


class ProductPriceAlert(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    stores = models.ManyToManyField(Store)
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    active_history = models.ForeignKey(
        "ProductPriceAlertHistory", on_delete=models.SET_NULL,
        blank=True, null=True)

    creation_date = models.DateTimeField(auto_now_add=True)

    def generate_current_history(self):
        pass

    class Meta:
        app_label = 'alerts'
        ordering = ('-creation_date',)
