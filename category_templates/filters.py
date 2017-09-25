from django_filters import rest_framework

from category_templates.models import CategoryTemplate
from solotodo.filter_querysets import create_category_filter


class CategoryTemplateFilterSet(rest_framework.FilterSet):
    @property
    def qs(self):
        qs = super(CategoryTemplateFilterSet, self).qs
        categories_with_permission = create_category_filter()(self.request)
        qs = qs.filter(category__in=categories_with_permission)
        return qs

    class Meta:
        model = CategoryTemplate
        fields = ('category', 'purpose', 'api_client')
