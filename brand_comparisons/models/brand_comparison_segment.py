from django.db import models

from .brand_comparison import BrandComparison


class BrandComparisonSegment(models.Model):
    name = models.CharField(max_length=512)
    ordering = models.IntegerField()
    comparison = models.ForeignKey(BrandComparison, on_delete=models.CASCADE,
                                   related_name='segments')

    def __str__(self):
        return '{} - {}'.format(self.name, self.comparison.name)

    class Meta:
        app_label = 'brand_comparisons'
        ordering = ('comparison', 'ordering',)
