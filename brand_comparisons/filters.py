from django_filters import rest_framework
from .models import BrandComparisonAlert


class BrandComparisonAlertFilterSet(rest_framework.FilterSet):
    class Meta:
        model = BrandComparisonAlert
        fields = ['brand_comparison']
