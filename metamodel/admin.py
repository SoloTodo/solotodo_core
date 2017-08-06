from django.contrib import admin
from django.contrib.admin import ModelAdmin
from metamodel.models import MetaModel, MetaField, InstanceModel, InstanceField


admin.site.register(MetaModel)


class MetaFieldAdmin(ModelAdmin):
    list_display = ['__str__', 'nullable', 'multiple', 'model']

admin.site.register(MetaField, MetaFieldAdmin)
admin.site.register(InstanceModel)
admin.site.register(InstanceField)
