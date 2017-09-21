from django.contrib import admin

from .models import CategoryTemplateTarget, CategoryTemplatePurpose, \
    CategoryTemplate

admin.site.register(CategoryTemplateTarget)
admin.site.register(CategoryTemplatePurpose)
admin.site.register(CategoryTemplate)
