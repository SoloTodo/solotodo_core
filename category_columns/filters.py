from django_filters import rest_framework

from category_columns.models import CategoryColumn, CategoryColumnPurpose
from solotodo.filter_querysets import create_category_filter


class CategoryColumnFilterSet(rest_framework.FilterSet):
    categories = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_category_filter(),
        name='field__category',
        label='Categories'
    )
    purposes = rest_framework.ModelMultipleChoiceFilter(
        queryset=CategoryColumnPurpose.objects.all(),
        name='purpose',
        label='Purposes'
    )

    @property
    def qs(self):
        qs = super(CategoryColumnFilterSet, self).qs

        qs = qs.prefetch_related(
            'field__category',
            'country',
            'purpose',
        )

        if self.request:
            categories_with_permission = create_category_filter()(
                self.request)
            qs = qs.filter(
                field__category__in=categories_with_permission,
            )

        return qs

    class Meta:
        model = CategoryColumn
        fields = ('purpose',)
