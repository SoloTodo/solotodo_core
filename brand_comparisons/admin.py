from django.contrib import admin

from .models import BrandComparison, BrandComparisonSegment, \
    BrandComparisonSegmentRow, BrandComparisonAlert


@admin.register(BrandComparison)
class BrandComparisonAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'brand_1', 'brand_2', 'price_type')
    readonly_fields = ('user', 'manual_products')


@admin.register(BrandComparisonSegment)
class SegmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'ordering', 'comparison')


@admin.register(BrandComparisonSegmentRow)
class SegmentRowAdmin(admin.ModelAdmin):
    list_display = ('ordering', 'product_1', 'product_2', 'segment')
    readonly_fields = ('product_1', 'product_2')
