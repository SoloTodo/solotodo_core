from django.db import models

from .brand_comparison_segment import BrandComparisonSegment
from solotodo.models import Product


class BrandComparisonSegmentRow(models.Model):
    ordering = models.IntegerField()
    product_1 = models.ForeignKey(Product, on_delete=models.CASCADE,
                                  related_name='product_1',
                                  null=True, blank=True)
    product_2 = models.ForeignKey(Product, on_delete=models.CASCADE,
                                  related_name='product_2',
                                  null=True, blank=True)
    segment = models.ForeignKey(BrandComparisonSegment,
                                on_delete=models.CASCADE,
                                related_name='rows')

    def __str__(self):
        return '{} - {} - {}'.format(self.segment.name,
                                     self.product_1, self.product_2)

    class Meta:
        app_label = 'brand_comparisons'
        ordering = ('segment', 'ordering',)
