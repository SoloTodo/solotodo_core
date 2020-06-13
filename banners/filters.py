from django_filters import rest_framework

from solotodo.custom_model_multiple_choice_filter import \
    CustomModelMultipleChoiceFilter
from solotodo.filter_utils import IsoDateTimeFromToRangeFilter
from solotodo.filter_querysets import \
    create_store_filter, create_category_filter

from solotodo.models import Brand, Category
from .models import \
    Banner, BannerUpdate, BannerAsset, BannerSection, BannerSubsectionType


class BannerFilterSet(rest_framework.FilterSet):
    timestamp = IsoDateTimeFromToRangeFilter(
        field_name='update__timestamp'
    )

    stores = CustomModelMultipleChoiceFilter(
        queryset=create_store_filter('view_store_banners'),
        field_name='update__store',
        label='Stores'
    )

    sections = CustomModelMultipleChoiceFilter(
        queryset=BannerSection.objects.all(),
        field_name='subsection__section',
        label='Sections'
    )

    asset = CustomModelMultipleChoiceFilter(
        queryset=BannerAsset.objects.all(),
        field_name='asset',
        label='Assets'
    )

    brands = CustomModelMultipleChoiceFilter(
        queryset=Brand.objects.all(),
        field_name='asset__contents__brand',
        label='Brand'
    )

    categories = CustomModelMultipleChoiceFilter(
        queryset=create_category_filter('view_category_report'),
        field_name='asset__contents__category',
        label='Category'
    )

    types = CustomModelMultipleChoiceFilter(
        queryset=BannerSubsectionType.objects.all(),
        field_name='subsection__type',
        label='Types'
    )

    creation_date = IsoDateTimeFromToRangeFilter(
        field_name='update__timestamp'
    )

    is_active = rest_framework.BooleanFilter(
        field_name='is_active', method='_is_active', label='Is active?')

    @property
    def qs(self):
        qs = super(BannerFilterSet, self).qs

        if self.request:
            qs = qs.filter_by_user_perms(self.request.user, 'view_banner')

        return qs

    def _is_active(self, queryset, name, value):
        if value:
            return queryset.get_active()
        else:
            return queryset.get_inactive()

    class Meta:
        model = Banner
        fields = ['update_id']


class BannerUpdateFilterSet(rest_framework.FilterSet):
    timestamp = IsoDateTimeFromToRangeFilter(
        field_name='timestamp'
    )

    stores = CustomModelMultipleChoiceFilter(
        queryset=create_store_filter('view_banners'),
        field_name='store',
        label='Stores'
    )

    is_active = rest_framework.BooleanFilter(
        field_name='is_active', method='_is_active', label='Is active?')

    ids = CustomModelMultipleChoiceFilter(
        queryset=BannerUpdate.objects.all(),
        method='_ids',
        label='BannerUpdates'
    )

    @property
    def qs(self):
        qs = super(BannerUpdateFilterSet, self).qs

        if self.request:
            qs = qs.filter_by_user_perms(self.request.user,
                                         'view_banner_update')

        return qs

    def _ids(self, queryset, name, value):
        if value:
            return queryset & value
        return queryset

    def _is_active(self, queryset, name, value):
        if value:
            return queryset.get_active()
        else:
            return queryset.get_inactive()

    class Meta:
        model = BannerUpdate
        fields = ['ids']


class BannerAssetFilterSet(rest_framework.FilterSet):
    creation_date = IsoDateTimeFromToRangeFilter(
        field_name='creation_date'
    )

    is_active = rest_framework.BooleanFilter(
        field_name='is_active', method='_is_active', label='Is active?')

    is_complete = rest_framework.BooleanFilter(
        field_name='is_complete', method='_is_complete', label='Is complete?'
    )

    @property
    def qs(self):
        qs = super(BannerAssetFilterSet, self).qs

        if self.request:
            qs = qs.filter_by_user_perms(self.request.user, 'view_banners')

        return qs

    def _is_active(self, queryset, name, value):
        if value:
            return queryset.get_active()
        else:
            return queryset.get_inactive()

    def _is_complete(self, queryset, name, value):
        if value:
            return queryset.get_complete()
        else:
            return queryset.get_incomplete()

    class Meta:
        model = BannerAsset
        fields = []
