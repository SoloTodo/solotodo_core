from rest_framework import serializers

from category_specs_forms.models import CategorySpecsFormFilter, \
    CategorySpecsFormFieldset, CategorySpecsFormOrder, \
    CategorySpecsFormLayout, CategorySpecsFormColumn
from metamodel.models import InstanceModel


class InstanceModelSerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.CharField(source='__str__')
    value = serializers.DecimalField(source='decimal_value', decimal_places=2,
                                     max_digits=10)

    class Meta:
        model = InstanceModel
        fields = ('id', 'name', 'value')


class CategorySpecsFormFilterSerializer(
        serializers.HyperlinkedModelSerializer):
    name = serializers.CharField(source='filter.name')
    type = serializers.CharField(source='filter.type')
    choices = InstanceModelSerializer(many=True)

    class Meta:
        model = CategorySpecsFormFilter
        fields = ['label', 'name', 'type', 'choices', 'continuous_range_step',
                  'continuous_range_unit']


class CategorySpecsFormFieldsetSerializer(
        serializers.HyperlinkedModelSerializer):
    filters = CategorySpecsFormFilterSerializer(many=True)

    class Meta:
        model = CategorySpecsFormFieldset
        fields = ['label', 'filters']


class CategorySpecsFormOrderSerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.CharField(source='order.name')

    class Meta:
        model = CategorySpecsFormOrder
        fields = ['name', 'label', 'suggested_use']


class CategorySpecsFormColumnSerializer(
        serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CategorySpecsFormColumn
        fields = ['field', 'label']


class CategorySpecsFormLayoutSerializer(
        serializers.HyperlinkedModelSerializer):
    fieldsets = CategorySpecsFormFieldsetSerializer(many=True)
    orders = CategorySpecsFormOrderSerializer(many=True)
    columns = CategorySpecsFormColumnSerializer(many=True)

    class Meta:
        model = CategorySpecsFormLayout
        fields = ['category', 'api_client', 'country', 'name', 'fieldsets',
                  'orders', 'columns']
