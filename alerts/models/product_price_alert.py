from django.db import models
from django.contrib.auth import get_user_model
from collections import OrderedDict

from solotodo.models import Product, Store, Entity


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

    def get_entities(self):
        return Entity.objects.filter(
            product=self.product, store__in=self.stores)\
            .order_by('offer_price').get_available()

    def update_active_history(self):
        from alerts.models import ProductPriceAlertHistory

        entries = []
        entities = self.get_entities()

        for entity in entities:
            entries.append(entity.active_registry)

        history = ProductPriceAlertHistory(
            alert=self,
            entries=entries
        )

        history.save()

        self.active_history = history
        self.save()

    def generate_delta_dict(self):
        entries = self.active_history.entries
        entities = self.get_entities()

        delta_dict = OrderedDict()

        for entity in entities:
            delta_dict[entity.id] = {
                "active": entity.active_registry
            }

        for entry in entries:
            if entry.entity.id in delta_dict:
                delta_dict[entry.entity.id]['previous'] = entry
            else:
                delta_dict[entry.entity.id] = {
                    "previous": entry
                }

        return delta_dict

    def check_for_changes(self):
        changed = False

        delta_list = self.generate_delta_dict()

        for item in delta_list:
            previous = item.get('previous')
            current = item.get('current')

            if not previous or not current or \
                    previous.offer_price != current.offer_price or \
                    previous.normal_price != current.normal_price:
                changed = True
                break

        if changed:
            self.send_email(delta_list)
            self.update_active_history()

    def send_email(self, delta_list=None):
        if not delta_list:
            delta_list = self.generate_delta_dict()

    class Meta:
        app_label = 'alerts'
        ordering = ('-creation_date',)
