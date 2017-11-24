from django.contrib import admin

from category_specs_forms.models import CategorySpecsFormLayout, \
    CategorySpecsFormFieldset, CategorySpecsFormFilter, \
    CategorySpecsFormOrder


@admin.register(CategorySpecsFormLayout)
class CategorySpecsFormLayoutModelAdmin(admin.ModelAdmin):
    list_display = ('category', 'website', 'name')
    list_filter = ('category', 'website')


@admin.register(CategorySpecsFormFieldset)
class CategorySpecsFormFieldsetModelAdmin(admin.ModelAdmin):
    list_display = ('layout', 'label', 'ordering')
    list_filter = ('layout__website', 'layout__category',)


@admin.register(CategorySpecsFormFilter)
class CategorySpecsFormFilterModelAdmin(admin.ModelAdmin):
    list_display = ('fieldset', 'label', 'ordering', 'country')
    list_filter = ('fieldset',)


@admin.register(CategorySpecsFormOrder)
class CategorySpecsFormOrderModelAdmin(admin.ModelAdmin):
    list_display = ('layout', 'label', 'suggested_use', 'ordering', 'country')
    list_filter = ('layout',)
