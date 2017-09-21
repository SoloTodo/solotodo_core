from django_filters import rest_framework
from rest_framework import viewsets

from category_templates.filters import CategoryTemplateFilterSet
from category_templates.models import CategoryTemplatePurpose, \
    CategoryTemplateTarget, CategoryTemplate
from category_templates.serializers import CategoryTemplatePurposeSerializer, \
    CategoryTemplateTargetSerializer, CategoryTemplateSerializer


class CategoryTemplatePurposeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CategoryTemplatePurpose.objects.all()
    serializer_class = CategoryTemplatePurposeSerializer


class CategoryTemplateTargetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CategoryTemplateTarget.objects.all()
    serializer_class = CategoryTemplateTargetSerializer


class CategoryTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CategoryTemplate.objects.all()
    serializer_class = CategoryTemplateSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, )
    filter_class = CategoryTemplateFilterSet
