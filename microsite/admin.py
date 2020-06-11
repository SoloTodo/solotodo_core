from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from .models import MicrositeBrand, MicrositeEntry


@admin.register(MicrositeBrand)
class MicrositeBrandAdmin(GuardedModelAdmin):
    list_display = ('name', 'brand', 'fields')


@admin.register(MicrositeEntry)
class MicrositeEntryAdmin(admin.ModelAdmin):
    list_display = (
        'brand', 'product', 'ordering', 'home_ordering', 'sku',
        'brand_url', 'title', 'subtitle', 'description',
        'reference_price', 'custom_attr_1_str')

    readonly_fields = ('product',)
