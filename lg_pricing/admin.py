from django.contrib import admin

from lg_pricing.models import LgRsBanner


@admin.register(LgRsBanner)
class LgRsBannerModelAdmin(admin.ModelAdmin):
    list_display = ('store_name', 'category_name', 'brand_name',
                    'subsection_name', 'timestamp', 'is_active')
    list_filter = ('store_name', 'category_name', 'brand_name', 'type_name',
                   'is_active')
