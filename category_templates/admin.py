from django import forms
from django.contrib import admin
from codemirror import CodeMirrorTextarea


from .models import CategoryTemplatePurpose, \
    CategoryTemplate

admin.site.register(CategoryTemplatePurpose)


class CategoryTemplateModelForm(forms.ModelForm):
    class Meta:
        model = CategoryTemplate
        fields = '__all__'
        widgets = {
            'body': CodeMirrorTextarea(
                mode="django",
                dependencies=("xml", 'htmlmixed'),
                addon_js=("mode/overlay",),
                theme="mdn-like",
                custom_css=("css/category_template_code_widget.css",),
                config={
                    'lineNumbers': True,
                    'tabSize': 2,
                    'indentWithTabs': True
                }
            )
        }


class CategoryTemplateModelAdmin(admin.ModelAdmin):
    form = CategoryTemplateModelForm
    list_filter = ['website', 'purpose', 'category']


admin.site.register(CategoryTemplate, CategoryTemplateModelAdmin)
