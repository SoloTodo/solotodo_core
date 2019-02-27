from django import forms
from django.core.exceptions import ValidationError

from solotodo.models import Store, Brand, Category
from banners.models import Banner, BannerAsset, BannerSection


class BannerActiveParticipationForm(forms.Form):
    stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all(),
        required=False)
    sections = forms.ModelMultipleChoiceField(
        queryset=BannerSection.objects.all(),
        required=False)
    brands = forms.ModelMultipleChoiceField(
        queryset=Brand.objects.all(),
        required=False)
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False)
    aggregation_field = forms.CharField()

    def get_banner_participation(self, request):
        stores = self.cleaned_data['stores']
        sections = self.cleaned_data['sections']
        brands = self.cleaned_data['brands']
        categories = self.cleaned_data['categories']
        aggregation_field = self.cleaned_data['aggregation_field']

        banners = Banner.objects.all()

        if stores:
            banners = banners.filter(update__store__in=stores)

        if sections:
            banners = banners.filter(subsection__section__in=sections)

        if brands:
            assets = BannerAsset.objects.filter(contents__brand__in=brands)
            banners = banners.filter(asset__in=assets)

        if categories:
            pass

        import ipdb
        ipdb.set_trace()
