from django_filters import rest_framework

from metamodel.models import InstanceModel, MetaModel


class InstanceFilterSet(rest_framework.FilterSet):
    models = rest_framework.ModelMultipleChoiceFilter(
        queryset=MetaModel.objects.all(),
        field_name='model',
        label='Models'
    )

    class Meta:
        model = InstanceModel
        fields = []
