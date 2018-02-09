from django import forms

from solotodo.models import Store


class StoresForm(forms.Form):
    stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all(),
        required=False
    )

    @classmethod
    def from_user(cls, user, data):
        form = cls(data)

        stores = Store.objects.filter_by_user_perms(user, 'view_store')

        form.fields['stores'].queryset = stores
        return form
