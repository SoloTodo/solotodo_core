from django import forms
from metamodel.models import InstanceModel


class MetaFieldMakeNonNullableMetaFieldForm(forms.Form):
    default = forms.ModelChoiceField(queryset=InstanceModel.objects.all(),
                                     required=True)

    def __init__(self, meta_field, data=None, *args, **kwargs):
        super(MetaFieldMakeNonNullableMetaFieldForm, self).__init__(
            data, *args, **kwargs)

        self.fields['default'].queryset = InstanceModel.objects.filter(
            model=meta_field.model)
