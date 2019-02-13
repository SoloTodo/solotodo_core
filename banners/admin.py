from django.contrib import admin

from .models import Banner, BannerUpdate, BannerAsset, BannerAssetContent


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('update', 'asset', 'position')
    readonly_fields = ('update', 'asset', 'position')


@admin.register(BannerUpdate)
class BannerUpdateAdmin(admin.ModelAdmin):
    list_display = ('store', 'timestamp')
    readonly_fields = ('store', 'timestamp')


@admin.register(BannerAsset)
class BannerAssetAdmin(admin.ModelAdmin):
    list_display = ('picture_url',)
    readonly_fields = ('picture_url',)


@admin.register(BannerAssetContent)
class BannerAssetContentAdmin(admin.ModelAdmin):
    list_display = ('asset', 'brand', 'category', 'percentage')
    readonly_fields = ('asset', 'brand', 'category', 'percentage')
