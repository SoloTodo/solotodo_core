from rest_framework import serializers

from category_templates.models import CategoryTemplatePurpose, \
    CategoryTemplate


class CategoryTemplatePurposeSerializer(
        serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CategoryTemplatePurpose
        fields = ('url', 'id', 'name')


class CategoryTemplateSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CategoryTemplate
        fields = ('url', 'id', 'category', 'purpose', 'website', 'body')
