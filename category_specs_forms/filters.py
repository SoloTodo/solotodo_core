from django_filters import rest_framework

from category_specs_forms.models import CategorySpecsFormLayout
from solotodo.filter_querysets import create_category_filter, \
    create_api_client_filter


class CategorySpecsFormLayoutFilterset(rest_framework.FilterSet):
    @property
    def qs(self):
        qs = super(CategorySpecsFormLayoutFilterset, self).qs

        qs = qs.prefetch_related(
            'fieldsets__filters__filter',
            'orders__order'
        )

        if self.request:
            categories_with_permission = create_category_filter()(
                self.request)
            qs = qs.filter(
                category__in=categories_with_permission,
            )

        return qs

    class Meta:
        model = CategorySpecsFormLayout
        fields = ('category', 'api_client', 'country')
