from django_filters import rest_framework

from metamodel.models import InstanceModel, MetaModel, MetaField, InstanceField


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


class InstanceFieldFilterSet(rest_framework.FilterSet):
    parents = rest_framework.ModelMultipleChoiceFilter(
        queryset=InstanceModel.objects.all(),
        field_name='parent',
        label='Parent'
    )

    class Meta:
        model = InstanceField
        fields = []
