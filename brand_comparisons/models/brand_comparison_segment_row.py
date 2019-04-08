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

    def move(self, direction):
        ordering = self.ordering
        segment = self.segment

        if direction == 'up':
            row = segment.rows.filter(ordering__lt=ordering).last()
        elif direction == 'down':
            row = segment.rows.filter(ordering__gt=ordering).first()
        else:
            raise Exception('Invalid direction')

        if not row:
            return

        self.ordering = 0
        self.save()
        row_ordering = row.ordering
        row.ordering = ordering
        row.save()
        self.ordering = row_ordering
        self.save()

    def __str__(self):
        return '{} - {} - {}'.format(self.segment.name,
                                     self.product_1, self.product_2)

    class Meta:
        app_label = 'brand_comparisons'
        unique_together = [('segment', 'ordering')]
        ordering = ('segment', 'ordering',)
