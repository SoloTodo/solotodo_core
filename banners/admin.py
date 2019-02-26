from django.contrib import admin

from .models import Banner, BannerUpdate, BannerAsset, BannerAssetContent, \
    BannerSection, BannerSubsection, BannerSubsectionType


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('update', 'asset', 'subsection', 'position')


@admin.register(BannerUpdate)
class BannerUpdateAdmin(admin.ModelAdmin):
    list_display = ('store', 'timestamp')


@admin.register(BannerAsset)
class BannerAssetAdmin(admin.ModelAdmin):
    list_display = ('key', 'picture_url',)


@admin.register(BannerAssetContent)
class BannerAssetContentAdmin(admin.ModelAdmin):
    list_display = ('asset', 'brand', 'category', 'percentage')


@admin.register(BannerSection)
class BannerSectionAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(BannerSubsection)
class BannerSubsectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'section', 'type')


@admin.register(BannerSubsectionType)
class BannerSubsectionType(admin.ModelAdmin):
    list_display = ('name', 'storescraper_name')
