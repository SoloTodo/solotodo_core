from django.db import models
from django.contrib.auth import get_user_model

from solotodo.models import Brand, Store, Category


class BrandComparison(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    name = models.CharField(max_length=512)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand_1 = models.ForeignKey(Brand, on_delete=models.CASCADE,
                                related_name='+')
    brand_2 = models.ForeignKey(Brand, on_delete=models.CASCADE,
                                related_name='+')
    price_type = models.CharField(
        max_length=512,
        choices=[('normal', 'Normal'), ('offer', 'Offer')],
        default='offer')
    stores = models.ManyToManyField(Store)

    def __str__(self):
        return '{} - {} - {} - {} - {}'.format(
            self.user, self.name, self.brand_1, self.brand_2, self.price_type)

    class Meta:
        app_label = 'brand_comparisons'
        ordering = ('user', 'name')
        permissions = (
            ['backend_list_brand_comparisons',
             'Can see brand comparisons in the backend'],
        )
