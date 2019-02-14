from django.contrib import admin

from .models import Banner, BannerUpdate, BannerAsset, BannerAssetContent


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('update', 'asset', 'position')


@admin.register(BannerUpdate)
class BannerUpdateAdmin(admin.ModelAdmin):
    list_display = ('store', 'timestamp')


@admin.register(BannerAsset)
class BannerAssetAdmin(admin.ModelAdmin):
    list_display = ('key', 'picture_url',)


@admin.register(BannerAssetContent)
class BannerAssetContentAdmin(admin.ModelAdmin):
    list_display = ('asset', 'brand', 'category', 'percentage')
