from rest_framework import serializers

from category_columns.models import CategoryColumn


class CategoryColumnSerializer(serializers.HyperlinkedModelSerializer):
    label = serializers.CharField(source='field.label')
    es_field = serializers.CharField(source='field.es_field')
    purpose = serializers.CharField(source='purpose.name')

    class Meta:
        model = CategoryColumn
        fields = ('label', 'es_field', 'purpose', 'country')
