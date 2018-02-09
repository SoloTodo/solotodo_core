from django.contrib.auth import get_user_model
from django.db import models

from solotodo.models import Product, Entity


class Budget(models.Model):
    name = models.CharField(max_length=255)
    is_public = models.BooleanField(default=False)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE,
                             related_name='budgets')
    creation_date = models.DateTimeField(auto_now_add=True)
    products_pool = models.ManyToManyField(Product, blank=True)

    def __str__(self):
        return self.name

    def select_cheapest_stores(self, stores):
        entities = Entity.objects.filter(
            product__in=self.products_pool.all(),
            store__in=stores
        ).get_available()\
            .order_by('active_registry__offer_price')\
            .select_related('product')

        product_to_cheapest_store_dict = {}

        for entity in entities:
            if entity.product not in product_to_cheapest_store_dict:
                product_to_cheapest_store_dict[entity.product] = entity.store

        for budget_entry in self.entries.filter(
                selected_product__isnull=False):
            new_selected_store = product_to_cheapest_store_dict.get(
                budget_entry.selected_product)
            if budget_entry.selected_store != new_selected_store:
                budget_entry.selected_store = new_selected_store
                budget_entry.save()

    class Meta:
        app_label = 'hardware'
        ordering = ['-pk']
