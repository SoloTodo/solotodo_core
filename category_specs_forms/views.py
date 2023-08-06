from rest_framework import viewsets
from django_filters import rest_framework

from category_specs_forms.filters import CategorySpecsFormLayoutFilterset
from category_specs_forms.models import CategorySpecsFormLayout
from category_specs_forms.serializers import CategorySpecsFormLayoutSerializer


class CategorySpecsFormLayoutViewset(viewsets.ReadOnlyModelViewSet):
    queryset = CategorySpecsFormLayout.objects.all()
    serializer_class = CategorySpecsFormLayoutSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, )
    filterset_class = CategorySpecsFormLayoutFilterset
