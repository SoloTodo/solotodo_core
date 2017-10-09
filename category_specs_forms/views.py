from rest_framework import viewsets

from category_specs_forms.models import CategorySpecsFormLayout
from category_specs_forms.serializers import CategorySpecsFormLayoutSerializer


class CategorySpecsFormLayoutViewset(viewsets.ReadOnlyModelViewSet):
    queryset = CategorySpecsFormLayout.objects.all()
    serializer_class = CategorySpecsFormLayoutSerializer

    def get_queryset(self):
        return CategorySpecsFormLayout.objects.prefetch_related(
            'fieldsets__filters__filter',
            'orders__order'
        )
