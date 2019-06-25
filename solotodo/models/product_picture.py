from django.db import models
from sorl.thumbnail import ImageField

from solotodo.models.product import Product


class ProductPictureQuerySet(models.QuerySet):
    def filter_by_user_perms(self, user, permission):
        synth_permissions = {
            'view_product_picture': {
                'product': 'view_product',
            }
        }

        assert permission in synth_permissions

        permissions = synth_permissions[permission]

        products_with_permissions = Product.objects.filter_by_user_perms(
            user, permissions['product'])

        return self.filter(
            product__in=products_with_permissions
        )


class ProductPicture(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='pictures')
    file = ImageField(upload_to='product_pictures', max_length=512)
    ordering = models.PositiveIntegerField()

    objects = ProductPictureQuerySet.as_manager()

    def __str__(self):
        return '{} - {}'.format(self.product, self.file)

    class Meta:
        app_label = 'solotodo'
        ordering = ('product', 'ordering')
