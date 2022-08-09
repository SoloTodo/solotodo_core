from django.contrib import admin
from .models import WebsiteSlideAsset, WebsiteSlide


@admin.register(WebsiteSlideAsset)
class ReportModelAdmin(admin.ModelAdmin):
    list_display = ('picture', 'theme_color')


@admin.register(WebsiteSlide)
class ReportModelAdmin(admin.ModelAdmin):
    list_display = ('destination_url', 'categories', '')