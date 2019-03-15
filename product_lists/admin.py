from django.contrib import admin

from .models import ProductList, ProductListEntry


@admin.register(ProductList)
class ProductListAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'category',
                    'creation_date', 'last_updated')
    readonly_fields = ('user',)


@admin.register(ProductListEntry)
class ProductListEntry(admin.ModelAdmin):
    list_display = ('product_list', 'product')
    readonly_fields = ('product',)
