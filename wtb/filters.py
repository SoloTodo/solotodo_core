from django.db.models import Q
from django_filters import rest_framework

from solotodo.filter_querysets import create_model_filter, \
    create_category_filter
from wtb.models import WtbBrand, WtbEntity, WtbBrandUpdateLog

create_wtb_brand_filter = create_model_filter(WtbBrand, 'view_wtb_brand')


class WtbEntityFilterSet(rest_framework.FilterSet):
    brands = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_wtb_brand_filter(),
        name='brand',
        label='Brands'
    )
    categories = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_category_filter(),
        name='category',
        label='Categories'
    )
    keys = rest_framework.CharFilter(
        name='key',
        label='Key'
    )

    is_associated = rest_framework.BooleanFilter(
        name='is_associated', method='_is_associated', label='Is associated?')

    @property
    def qs(self):
        qs = super(WtbEntityFilterSet, self).qs.select_related(
            'brand',
            'category',
            'product'
        )

        brands_with_permission = create_wtb_brand_filter()(self.request)
        categories_with_permission = create_category_filter()(self.request)

        return qs.filter(
            Q(brand__in=brands_with_permission) &
            Q(category__in=categories_with_permission))

    def _is_associated(self, queryset, name, value):
        return queryset.filter(product__isnull=not value)

    class Meta:
        model = WtbEntity
        fields = ['is_active', 'is_visible', 'product']


class WtbEntityStaffFilterSet(rest_framework.FilterSet):
    brands = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_wtb_brand_filter('is_wtb_brand_staff'),
        name='brand',
        label='Brands'
    )
    categories = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_category_filter('is_category_staff'),
        name='category',
        label='Categories'
    )

    @property
    def qs(self):
        qs = super(WtbEntityStaffFilterSet, self).qs.select_related(
            'product__instance_model',
        )
        if self.request:
            qs = qs.filter_by_user_perms(
                self.request.user, 'is_wtb_entity_staff')
        return qs


class WtbBrandUpdateLogFilterSet(rest_framework.FilterSet):
    @property
    def qs(self):
        qs = super(WtbBrandUpdateLogFilterSet, self).qs
        brands_with_permission = create_wtb_brand_filter()(self.request)
        qs = qs.filter(brand__in=brands_with_permission)
        return qs

    class Meta:
        model = WtbBrandUpdateLog
        fields = ('brand',)
