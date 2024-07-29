from django.db.models import Q
from django_filters import rest_framework

from solotodo.custom_model_multiple_choice_filter import CustomModelMultipleChoiceFilter
from solotodo.filter_querysets import (
    create_model_filter,
    create_category_filter,
    create_store_filter,
    create_product_filter,
)
from wtb.models import WtbBrand, WtbEntity, WtbBrandUpdateLog

create_wtb_brand_filter = create_model_filter(WtbBrand, "view_wtb_brand")


class WtbEntityFilterSet(rest_framework.FilterSet):
    brands = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_wtb_brand_filter(), field_name="brand", label="Brands"
    )
    categories = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_category_filter(), field_name="category", label="Categories"
    )
    keys = rest_framework.CharFilter(field_name="key", label="Key")
    products = rest_framework.ModelChoiceFilter(
        queryset=create_product_filter(), field_name="product", label="Products"
    )
    is_associated = rest_framework.BooleanFilter(
        field_name="is_associated", method="_is_associated", label="Is associated?"
    )
    lg_product_comparison = rest_framework.BooleanFilter(
        field_name="lg_product_comparison",
        method="_lg_product_comparison",
        label="Is it for LG Product Comparison site?",
    )
    lg_emotional_pdp = rest_framework.BooleanFilter(
        field_name="lg_emotional_pdp",
        method="_lg_emotional_pdp",
        label="Is it for LG Emotional PDP site?",
    )

    @property
    def qs(self):
        qs = super(WtbEntityFilterSet, self).qs.select_related(
            "brand", "category", "product"
        )

        brands_with_permission = create_wtb_brand_filter()(self.request)

        # Formally we would need to filter the categories to allow access only
        # to those the user has permission, but for the WTB service we
        # allow full read access to allow querying categories that SoloTodo
        # does not fully support (such as projectors and accesories)

        # categories_with_permission = create_category_filter()(self.request)

        return qs.filter(
            Q(brand__in=brands_with_permission)
            # & Q(category__in=categories_with_permission)
        )

    def _is_associated(self, queryset, name, value):
        return queryset.filter(product__isnull=not value)

    def _lg_product_comparison(self, queryset, name, value):
        # Product comparison entities have JSON in their description that starts with '['
        return queryset.filter(
            description__startswith="[", description__endswith="]", is_active=True
        )

    def _lg_emotional_pdp(self, queryset, name, value):
        # Emotional PDP entities have HTML in their description that starts with '<'
        return queryset.filter(
            description__startswith="<", description__endswith=">", is_active=True
        )

    class Meta:
        model = WtbEntity
        fields = ["is_active", "is_visible", "product"]


class WtbEntityStaffFilterSet(rest_framework.FilterSet):
    brands = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_wtb_brand_filter("is_wtb_brand_staff"),
        field_name="brand",
        label="Brands",
    )
    categories = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_category_filter("is_category_staff"),
        field_name="category",
        label="Categories",
    )

    @property
    def qs(self):
        qs = super(WtbEntityStaffFilterSet, self).qs.select_related(
            "product__instance_model",
        )
        if self.request:
            qs = qs.filter_by_user_perms(self.request.user, "is_wtb_entity_staff")
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
        fields = ("brand",)


class WtbStoreFilterSet(rest_framework.FilterSet):
    stores = CustomModelMultipleChoiceFilter(
        queryset=create_store_filter(), method="_ids", label="Stores"
    )

    def _ids(self, queryset, name, value):
        if value:
            return queryset & value
        return queryset
