from django_filters import rest_framework

from metamodel.models import InstanceModel, MetaModel, MetaField


class InstanceFilterSet(rest_framework.FilterSet):
    models = rest_framework.ModelMultipleChoiceFilter(
        queryset=MetaModel.objects.all(),
        field_name='model',
        label='Models'
    )

    class Meta:
        model = InstanceModel
        fields = []


class MetaFieldFilterSet(rest_framework.FilterSet):
    models = rest_framework.ModelMultipleChoiceFilter(
        queryset=MetaModel.objects.all(),
        field_name='model',
        label='Models'
    )

    class Meta:
        model = MetaField
        fields = []
