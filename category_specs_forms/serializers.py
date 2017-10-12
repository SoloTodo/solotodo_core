from rest_framework import serializers

from category_specs_forms.models import CategorySpecsFormFilter, \
    CategorySpecsFormFieldset, CategorySpecsFormOrder, CategorySpecsFormLayout


class CategorySpecsFormFilterSerializer(
        serializers.HyperlinkedModelSerializer):
    name = serializers.CharField(source='filter.name')
    type = serializers.CharField(source='filter.type')

    class Meta:
        model = CategorySpecsFormFilter
        fields = ['label', 'name', 'type', 'continuous_range_step',
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


class CategorySpecsFormLayoutSerializer(
        serializers.HyperlinkedModelSerializer):
    fieldsets = CategorySpecsFormFieldsetSerializer(many=True)
    orders = CategorySpecsFormOrderSerializer(many=True)

    class Meta:
        model = CategorySpecsFormLayout
        fields = ['category', 'api_client', 'country', 'name', 'fieldsets',
                  'orders']
