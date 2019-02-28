from django import forms
from django.db.models import F, Sum, Avg

from solotodo.models import Store, Brand, Category
from banners.models import Banner, BannerSection


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
    grouping_field = forms.ChoiceField(choices=(
        ('brand', 'Marca'),
        ('category', 'Categoría'),
        ('section', 'Sección'),
        ('subsection_type', 'Tipo subsección'),
        ('store', 'Tienda')
    ))

    def get_banner_participation(self):
        stores = self.cleaned_data['stores']
        sections = self.cleaned_data['sections']
        brands = self.cleaned_data['brands']
        categories = self.cleaned_data['categories']
        grouping_field = self.cleaned_data['grouping_field']

        banners = Banner.objects.filter(
            asset__contents__percentage__isnull=False)

        if stores:
            banners = banners.filter(update__store__in=stores)

        if sections:
            banners = banners.filter(subsection__section__in=sections)

        if brands:
            banners = banners.filter(asset__contents__brand__in=brands)

        if categories:
            banners = banners.filter(asset__contents__category__in=categories)

        db_grouping_fields = {
            'brand': 'asset__contents__brand',
            'category': 'asset__contents__category',
            'section': 'subsection__section',
            'subsection_type': 'subsection__type',
            'store': 'update__store'
        }

        db_grouping_field = db_grouping_fields[grouping_field]

        total_participation = banners.aggregate(
            Sum('asset__contents__percentage'))[
            'asset__contents__percentage__sum']

        banner_aggs = banners.order_by(db_grouping_field)\
            .values(db_grouping_field)\
            .annotate(
            grouping_label=F(db_grouping_field+'__name'),
            participation_score=Sum('asset__contents__percentage'),
            position_avg=Avg('position')
        ).order_by('-participation_score')

        banner_aggs_result = []

        for agg in banner_aggs:
            banner_aggs_result.append({
                'grouping_label': agg['grouping_label'],
                'participation_score': agg['participation_score'],
                'participation_percentage':
                    agg['participation_score']*100/total_participation,
                'position_avg': agg['position_avg']
            })

        return banner_aggs_result
