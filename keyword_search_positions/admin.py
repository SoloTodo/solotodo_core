from django.contrib import admin

from .models import KeywordSearch, KeywordSearchUpdate, \
    KeywordSearchEntityPosition


@admin.register(KeywordSearch)
class KeywordSearchAdmin(admin.ModelAdmin):
    list_display = ('user', 'store', 'category', 'keyword',
                    'threshold', 'creation_date')
    readonly_fields = ('user',)


@admin.register(KeywordSearchUpdate)
class KeywordSearchUpdateAdmin(admin.ModelAdmin):
    list_display = ('search', 'creation_date', 'status', 'message')


@admin.register(KeywordSearchEntityPosition)
class KeywordSearchEntityPositionAdmin(admin.ModelAdmin):
    list_display = ('entity', 'update', 'value')
    readonly_fields = ('entity', )
