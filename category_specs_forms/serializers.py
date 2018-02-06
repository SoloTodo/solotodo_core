from rest_framework import serializers

from category_specs_forms.models import CategorySpecsFormFilter, \
    CategorySpecsFormFieldset, CategorySpecsFormOrder, \
    CategorySpecsFormLayout
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
        fields = ['id', 'label', 'name', 'type', 'country',
                  'continuous_range_step', 'continuous_range_unit', 'choices']


class CategorySpecsFormFieldsetSerializer(
        serializers.HyperlinkedModelSerializer):
    filters = CategorySpecsFormFilterSerializer(many=True)

    class Meta:
        model = CategorySpecsFormFieldset
        fields = ['id', 'label', 'filters']


class CategorySpecsFormOrderSerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.CharField(source='order.name')

    class Meta:
        model = CategorySpecsFormOrder
        fields = ['id', 'name', 'label', 'suggested_use', 'country']


class CategorySpecsFormLayoutSerializer(
        serializers.HyperlinkedModelSerializer):
    fieldsets = CategorySpecsFormFieldsetSerializer(many=True)
    orders = CategorySpecsFormOrderSerializer(many=True)

    class Meta:
        model = CategorySpecsFormLayout
        fields = ['id', 'category', 'website', 'name', 'fieldsets', 'orders']
