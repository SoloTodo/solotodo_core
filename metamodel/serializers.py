from rest_framework import serializers

from metamodel.models import MetaModel, MetaField, InstanceModel, InstanceField


class MetaModelWithoutFieldsSerializer(serializers.HyperlinkedModelSerializer):
    is_primitive = serializers.BooleanField()

    class Meta:
        model = MetaModel
        fields = ['url', 'is_primitive', 'id', 'name', 'unicode_template',
                  'ordering_field']


class MetaFieldSerializer(serializers.HyperlinkedModelSerializer):
    model = MetaModelWithoutFieldsSerializer()
    parent = MetaModelWithoutFieldsSerializer()

    class Meta:
        model = MetaField
        fields = ['url', 'id', 'name', 'ordering', 'nullable',
                  'multiple', 'hidden', 'model', 'parent', 'help_text']


class MetaModelAddFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetaField
        fields = ['parent', 'name', 'ordering', 'nullable',
                  'multiple', 'hidden', 'model', 'help_text']


class MetaModelSerializer(serializers.HyperlinkedModelSerializer):
    fields = MetaFieldSerializer(many=True)

    class Meta:
        model = MetaModel
        fields = [
            'url', 'id', 'name', 'unicode_template', 'ordering_field',
            'fields']


class InstanceModelWithoutMetamodelSerializer(
        serializers.HyperlinkedModelSerializer):
    class Meta:
        model = InstanceModel
        fields = ['id', 'url', 'decimal_value', 'unicode_value',
                  'unicode_representation']


class InstanceFieldSerializer(serializers.HyperlinkedModelSerializer):
    parent = InstanceModelWithoutMetamodelSerializer()
    field = MetaFieldSerializer()
    value = InstanceModelWithoutMetamodelSerializer()

    class Meta:
        model = InstanceField
        fields = ['id', 'url', 'parent', 'field', 'value']


class InstanceModelSerializer(serializers.HyperlinkedModelSerializer):
    model = MetaModelSerializer()
    fields = InstanceFieldSerializer(many=True)

    class Meta:
        model = InstanceModel
        fields = ['id', 'url', 'decimal_value', 'unicode_value',
                  'unicode_representation', 'model', 'fields']


class MetaFieldPlainSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetaField
        fields = ['id', 'name', 'parent_id', 'nullable', 'multiple', 'model_id',
                  'ordering', 'hidden', 'help_text']


class MetaModelPlainSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetaModel
        fields = ['id', 'name', 'unicode_template', 'ordering_field']


class InstanceFieldPlainSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstanceField
        fields = ['id', 'field_id', 'value_id', 'parent_id']

class InstanceModelPlainSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstanceModel
        fields = ['id', 'decimal_value', 'unicode_value',
                  'unicode_representation', 'model_id']
