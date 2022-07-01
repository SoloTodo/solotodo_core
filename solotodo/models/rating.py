from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from solotodo.models import Category
from solotodo_core.s3utils import MediaRootPrivateS3Boto3Storage
from .product import Product
from .store import Store


class RatingQuerySet(models.QuerySet):
    def filter_by_user_perms(self, user, permission):
        synth_permissions = {
            'view_rating': {
                'store': 'view_store',
                'category': 'view_category',
            }
        }

        assert permission in synth_permissions

        permissions = synth_permissions[permission]

        perm_stores = Store.objects.filter_by_user_perms(
            user, permissions['store'])
        perm_categories = Category.objects.filter_by_user_perms(
            user, permissions['category'])

        return self.filter(
            store__in=perm_stores,
            product__instance_model__model__category__in=perm_categories,
        )


class Rating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    store_rating = models.IntegerField()
    store_comments = models.TextField()
    product_rating = models.IntegerField(blank=True, null=True)
    product_comments = models.TextField(blank=True, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    purchase_proof = models.FileField(
        upload_to='ratings', storage=MediaRootPrivateS3Boto3Storage())
    approval_date = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    ip = models.GenericIPAddressField()
    email_or_phone = models.CharField(max_length=255, blank=True, null=True)

    objects = RatingQuerySet.as_manager()

    def __str__(self):
        return '{}: {}'.format(self.product, self.store)

    def approve(self):
        if self.approval_date:
            raise ValidationError('Rating already approved')

        self.approval_date = timezone.now()
        self.save()

    class Meta:
        ordering = ['-pk']
        app_label = 'solotodo'
        permissions = [
            ('view_pending_ratings',
             'Can view the ratings pending for approval'),
            ('is_ratings_staff',
             'Has staff permissions over all the ratings'),
            ('backend_list_ratings', 'View rating list in backend')
        ]
