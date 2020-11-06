from rest_framework import serializers

from metamodel.models import MetaModel, MetaField, InstanceModel


class MetaModelWithoutFieldsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = MetaModel
        fields = ['url', 'id', 'name', 'unicode_template', 'ordering_field']


class MetaFieldSerializer(serializers.HyperlinkedModelSerializer):
    model = MetaModelWithoutFieldsSerializer()

    class Meta:
        model = MetaField
        fields = ['name', 'ordering', 'nullable', 'multiple', 'hidden',
                  'model']


class MetaModelSerializer(serializers.HyperlinkedModelSerializer):
    fields = MetaFieldSerializer(many=True)

    class Meta:
        model = MetaModel
        fields = [
            'url', 'id', 'name', 'unicode_template', 'ordering_field',
            'fields']


class InstanceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = InstanceModel
        fields = ['id', 'url', 'decimal_value', 'unicode_value',
                  'unicode_representation']
