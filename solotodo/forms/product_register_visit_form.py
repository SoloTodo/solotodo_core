from django import forms
from guardian.shortcuts import get_objects_for_user

from solotodo.models import Website


class ProductRegisterVisitForm(forms.Form):
    website = forms.ModelChoiceField(
        queryset=Website.objects.all()
    )

    @classmethod
    def from_user(cls, user, data):
        form = cls(data)

        websites = get_objects_for_user(user, 'view_website', Website)

        form.fields['website'].queryset = websites
        return form
