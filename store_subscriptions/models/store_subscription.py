from django.db import models
from django.contrib.auth import get_user_model

from solotodo.models import Store, Category, Entity


class StoreSubscription(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    categories = models.ManyToManyField(Category)
    creation_date = models.DateTimeField(auto_now_add=True)

    def send_update(self):
        entities = Entity.objects.filter(
            store=self.store,
            category__in=self.categories)

        for entity in entities:
            pass

    class Meta:
        app_label = 'store_subscriptions'
        ordering = ('-creation_date',)
