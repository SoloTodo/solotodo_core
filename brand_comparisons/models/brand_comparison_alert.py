from django.db import models
from django.contrib.auth import get_user_model

from .brand_comparison import BrandComparison
from solotodo.models import Store, Entity, EntityHistory


class BrandComparisonAlert(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    brand_comparison = models.ForeignKey(
        BrandComparison, on_delete=models.CASCADE)
    stores = models.ManyToManyField(Store)
    last_check = models.DateTimeField()

    def check_for_changes(self):
        changed = False

        for segment in self.brand_comparison.segments.all():
            for row in segment.rows.all():
                for store in self.stores.all():
                    try:
                        entity = Entity.objects.get(
                            store=store, product=row.product_1)
                    except Entity.DoesNotExist:
                        continue

                    last_registry = EntityHistory.objects.get(
                        entity=entity,
                        timestamp_lte=self.last_check)

    class Meta:
        app_label = 'brand_comparisons'
        ordering = ('user',)
