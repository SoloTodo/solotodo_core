from django.forms import ModelForm
from metamodel.models import MetaModel


class MetaModelForm(ModelForm):
    class Meta:
        model = MetaModel
        fields = ['name', 'unicode_template', 'ordering_field']
