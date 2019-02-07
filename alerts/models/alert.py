from django.db import models

from solotodo.models import Product, EntityHistory, Store, Entity


class Alert(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                null=True, blank=True)
    normal_price_registry = models.ForeignKey(
        EntityHistory, blank=True, null=True, on_delete=models.CASCADE,
        related_name='+')
    offer_price_registry = models.ForeignKey(
        EntityHistory, blank=True, null=True, on_delete=models.CASCADE,
        related_name='+')
    stores = models.ManyToManyField(Store)
    creation_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '{}'.format(self.product)

    @classmethod
    def find_optimum_entity_history(cls, product, stores, pricing_type):
        es = Entity.objects.filter(
            product=product, store__in=stores,
            active_registry__cell_monthly_payment__isnull=True)\
            .get_available().order_by(
                'active_registry__{}_price'.format(pricing_type))

        if es:
            return es[0].active_registry
        else:
            return None

    def update(self):
        assert self.product is not None

        new_normal_price_registry = self.find_optimum_entity_history(
            self.product, self.stores.all(), 'normal')
        new_offer_price_registry = self.find_optimum_entity_history(
            self.product, self.stores.all(), 'offer')

        # Update the alert pricing registry
        self.normal_price_registry = new_normal_price_registry
        self.offer_price_registry = new_offer_price_registry
        self.save()

    class Meta:
        app_label = 'alerts'
        ordering = ('-creation_date', )
