from rest_framework import serializers

from category_templates.models import CategoryTemplatePurpose, \
    CategoryTemplateTarget, CategoryTemplate


class CategoryTemplatePurposeSerializer(
        serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CategoryTemplatePurpose
        fields = ('url', 'id', 'name')


class CategoryTemplateTargetSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CategoryTemplateTarget
        fields = ('url', 'id', 'name')


class CategoryTemplateSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CategoryTemplate
        fields = ('url', 'id', 'category', 'purpose', 'target', 'body')
