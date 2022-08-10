from django.contrib import admin
from .models import WebsiteSlideAsset, WebsiteSlide


@admin.register(WebsiteSlideAsset)
class ReportModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'picture', 'theme_color')


@admin.register(WebsiteSlide)
class ReportModelAdmin(admin.ModelAdmin):
    list_display = ('destination_url', 'category_priority', 'home_priority')
