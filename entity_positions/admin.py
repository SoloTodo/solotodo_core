from django.contrib import admin

from .models import EntityPosition, EntityPositionSection


@admin.register(EntityPosition)
class EntityPositionAdmin(admin.ModelAdmin):
    list_display = ('entity_history', 'section', 'value')
    readonly_fields = ('entity_history',)


@admin.register(EntityPositionSection)
class EntityPositionSectionAdmin(admin.ModelAdmin):
    list_display = ('store', 'name')
