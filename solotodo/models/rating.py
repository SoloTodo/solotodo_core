from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from solotodo_core.s3utils import MediaRootPrivateS3Boto3Storage
from .product import Product
from .store import Store


class Rating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    store_rating = models.IntegerField()
    store_comments = models.TextField()
    product_rating = models.IntegerField()
    product_comments = models.TextField()
    creation_date = models.DateTimeField(auto_now_add=True)
    purchase_proof = models.FileField(
        upload_to='ratings', storage=MediaRootPrivateS3Boto3Storage())
    approval_date = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    ip = models.GenericIPAddressField()

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
