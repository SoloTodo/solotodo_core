from django import forms


class MetaFieldMakeNonNullablePrimitiveForm(forms.Form):
    default = forms.CharField(required=True, max_length=255)

    def __init__(self, meta_field, data=None, *args, **kwargs):
        super(MetaFieldMakeNonNullablePrimitiveForm, self).__init__(
            data, *args, **kwargs)

        try:
            field_klass = getattr(forms, meta_field.model.name)

            if meta_field.model.name == 'BooleanField':
                required = False
            else:
                required = True

            field = field_klass(required=required)

        except AttributeError:
            field = forms.ModelChoiceField(
                queryset=meta_field.model.instancemodel_set.all(),
                required=True
            )

        self.fields['default'] = field
