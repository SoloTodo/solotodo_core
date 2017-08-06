from django import forms
from metamodel.models import MetaField


class MetaFieldForm(forms.ModelForm):
    def clean(self):
        d = super(MetaFieldForm, self).clean()

        instance = self.instance

        if d['hidden'] and not instance.nullable and not instance.multiple:
            raise forms.ValidationError(
                'Hidden fields must be either nullable or multiple')

        return d

    class Meta:
        model = MetaField
        fields = ['name', 'hidden']
