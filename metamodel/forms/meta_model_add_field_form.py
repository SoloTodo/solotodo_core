from django import forms
from metamodel.models import MetaField


class MetaModelAddFieldForm(forms.ModelForm):
    def clean(self):
        d = super(MetaModelAddFieldForm, self).clean()

        if d['hidden'] and not d['nullable'] and not d['multiple']:
            raise forms.ValidationError('Hidden fields must be either '
                                        'nullable or multiple')

        return d

    class Meta:
        model = MetaField
        fields = ['name', 'model', 'nullable', 'multiple', 'hidden',
                  'help_text']
