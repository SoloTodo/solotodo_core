from django.contrib import admin

from category_columns.models import CategoryField, CategoryColumnPurpose, \
    CategoryColumn


@admin.register(CategoryField)
class CategoryFieldModelAdmin(admin.ModelAdmin):
    list_display = ('label', 'category', 'es_field')
    list_filter = ('category', )


admin.site.register(CategoryColumnPurpose)


@admin.register(CategoryColumn)
class CategoryColumnModelAdmin(admin.ModelAdmin):
    list_display = ('field_label', 'field_category', 'es_field', 'purpose',
                    'country', 'ordering')
    list_filter = ('field__category', )

    def get_queryset(self, request):
        qs = super(CategoryColumnModelAdmin, self).get_queryset(request)
        qs = qs.select_related('field__category', 'country', 'purpose')
        return qs

    def field_label(self, obj):
        return obj.field.label

    def field_category(self, obj):
        return obj.field.category

    def es_field(self, obj):
        return obj.field.es_field
