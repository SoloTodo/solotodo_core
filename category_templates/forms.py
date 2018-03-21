from django import forms
from guardian.shortcuts import get_objects_for_user

from category_templates.models import CategoryTemplatePurpose
from solotodo.models import Website


class ProductRenderForm(forms.Form):
    website = forms.ModelChoiceField(
        queryset=Website.objects.all()
    )
    purpose = forms.ModelChoiceField(
        queryset=CategoryTemplatePurpose.objects.all()
    )

    @classmethod
    def from_user(cls, user, data):
        valid_websites = get_objects_for_user(
            user, 'view_website', Website)

        form = cls(data)
        form.fields['website'].queryset = valid_websites

        return form
