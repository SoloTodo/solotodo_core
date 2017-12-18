from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from wtb.models import WtbBrand, WtbEntity, WtbBrandUpdateLog


@admin.register(WtbBrand)
class WtbBrandModelAdmin(GuardedModelAdmin):
    list_display = ('__str__', 'storescraper_class')


@admin.register(WtbEntity)
class WtbEntityModelAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'brand', 'category', 'product', 'name', 'key')
    list_filter = ('brand', 'category')
    readonly_fields = ('product', )


@admin.register(WtbBrandUpdateLog)
class WtbBrandUpdateLogModelAdmin(admin.ModelAdmin):
    list_display = ('brand', 'status', 'creation_date', 'last_updated',
                    'status')
    list_filter = ('brand', )
