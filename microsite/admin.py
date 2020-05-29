from django.contrib import admin

from .models import MicrositeBrand, MicrositeEntry


@admin.register(MicrositeBrand)
class MicrositeBrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'fields')


@admin.register(MicrositeEntry)
class MicrositeEntryAdmin(admin.ModelAdmin):
    list_display = (
        'brand', 'product', 'ordering', 'home_ordering', 'sku',
        'brand_url', 'title', 'description', 'reference_price',
        'custom_attr_1_str')

    readonly_fields = ('product',)
