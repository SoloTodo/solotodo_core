from django.db import models

from .brand_comparison import BrandComparison


class BrandComparisonSegment(models.Model):
    name = models.CharField(max_length=512)
    ordering = models.IntegerField()
    comparison = models.ForeignKey(BrandComparison, on_delete=models.CASCADE,
                                   related_name='segments')

    def move(self, direction):
        ordering = self.ordering
        comparison = self.comparison

        if direction == 'up':
            segment = comparison.segments.filter(ordering__lt=ordering).last()
        elif direction == 'down':
            segment = comparison.segments.filter(ordering__gt=ordering).first()
        else:
            raise Exception('Invalid direction')

        if not segment:
            return

        self.ordering = 0
        self.save()
        segment_ordering = segment.ordering
        segment.ordering = ordering
        segment.save()
        self.ordering = segment_ordering
        self.save()

    def add_row(self, ordering):
        from .brand_comparison_segment_row import BrandComparisonSegmentRow
        if not ordering:
            ordering = self.rows.last().ordering + 1

        update_rows = self.rows.filter(ordering__gte=ordering) \
            .order_by('-ordering')

        for row in update_rows:
            row.ordering += 1
            row.save()

        BrandComparisonSegmentRow.objects.create(
            ordering=ordering,
            segment=self)

    def __str__(self):
        return '{} - {}'.format(self.name, self.comparison.name)

    class Meta:
        app_label = 'brand_comparisons'
        unique_together = [('comparison', 'ordering')]
        ordering = ('comparison', 'ordering',)
