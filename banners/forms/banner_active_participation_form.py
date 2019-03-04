import io
import xlsxwriter

from django import forms
from django.core.files.base import ContentFile
from django.db.models import F, Sum, Avg
from guardian.shortcuts import get_objects_for_user

from solotodo.models import Store, Brand, Category
from solotodo_core.s3utils import PrivateS3Boto3Storage
from banners.models import Banner, BannerSection, BannerSubsectionType


class BannerActiveParticipationForm(forms.Form):
    fields_data = {
        'brand': {
            'label': 'Marca',
            'db_name': 'asset__contents__brand'
        },
        'category': {
            'label': 'Categoría',
            'db_name': 'asset__contents__category'
        },
        'section': {
            'label': 'Sección',
            'db_name': 'subsection__section'
        },
        'subsection_type': {
            'label': 'Tipo de página',
            'db_name': 'subsection__type'
        },
        'store': {
            'label': 'Tienda',
            'db_name': 'update__store'
        }
    }
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
    subsection_types = forms.ModelMultipleChoiceField(
        queryset=BannerSubsectionType.objects.all(),
        required=False)

    grouping_field = forms.ChoiceField(choices=[
        (key, value['label'])
        for key, value in fields_data.items()
    ])
    response_format = forms.CharField(required=False)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        valid_stores = get_objects_for_user(user, 'view_store_banners', Store)
        self.fields['stores'].queryset = valid_stores

    def get_filtered_banners(self):
        stores = self.cleaned_data['stores']
        sections = self.cleaned_data['sections']
        brands = self.cleaned_data['brands']
        categories = self.cleaned_data['categories']
        subsection_types = self.cleaned_data['subsection_types']

        banners = Banner.objects.get_active().filter(
            asset__contents__percentage__isnull=False
        )

        if stores:
            banners = banners.filter(update__store__in=stores)

        if sections:
            banners = banners.filter(subsection__section__in=sections)

        if subsection_types:
            banners = banners.filter(subsection__type__in=subsection_types)

        if brands:
            banners = banners.filter(asset__contents__brand__in=brands)

        if categories:
            banners = banners.filter(asset__contents__category__in=categories)

        return banners

    def get_common_aggs(self, banners):
        grouping_field = self.cleaned_data['grouping_field']
        db_grouping_field = self.fields_data[grouping_field]['db_name']
        total_participation = banners.aggregate(
            Sum('asset__contents__percentage'))[
            'asset__contents__percentage__sum']

        banner_aggs = banners.order_by(db_grouping_field) \
            .values(db_grouping_field) \
            .annotate(
            grouping_label=F(db_grouping_field + '__name'),
            participation_score=Sum('asset__contents__percentage'),
            position_avg=Avg('position')
        ).order_by('-participation_score')

        banner_aggs_result = []

        for agg in banner_aggs:
            banner_aggs_result.append({
                'grouping_label': agg['grouping_label'],
                'participation_score': agg['participation_score'],
                'participation_percentage':
                    agg['participation_score'] * 100 / total_participation,
                'position_avg': agg['position_avg']
            })

        return banner_aggs_result

    def get_banner_participation_as_json(self):
        banners = self.get_filtered_banners()
        banner_aggs_result = self.get_common_aggs(banners)

        return banner_aggs_result

    def get_banner_participation_as_xls(self):
        banners = self.get_filtered_banners()\
            .select_related(
            'update__store',
            'subsection__section',
            'subsection__type')

        # # # XLS  SPECIFIC AGGS # # #
        grouping_field = self.cleaned_data['grouping_field']
        db_grouping_field = self.fields_data[grouping_field]['db_name']

        total_participation = banners.aggregate(
            Sum('asset__contents__percentage'))[
            'asset__contents__percentage__sum']

        banner_aggs = banners.order_by('id', db_grouping_field)\
            .values('id', db_grouping_field+'__name') \
            .annotate(
            grouping_label=F(db_grouping_field + '__name'),
            participation_score=Sum('asset__contents__percentage')
        )

        banners_dict = {b.id: b for b in banners}

        # # # COMMON AGGS # # #
        global_aggs = self.get_common_aggs(banners)

        # # # REPORT # # #
        output = io.BytesIO()

        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10
        })

        url_format = workbook.add_format({
            'font_color': 'blue',
            'font_size': 10
        })

        # # # 1st WORKSHEET: COMMON AGGS # # #
        worksheet = workbook.add_worksheet()

        headers = [
            self.fields_data[grouping_field]['label'],
            'Participación (puntaje)',
            'Participación (porcentaje)',
            'Posición promedio'
        ]

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1

        for agg in global_aggs:
            col = 0
            worksheet.write(row, col, agg['grouping_label'])

            col += 1
            worksheet.write(row, col, agg['participation_score'])

            col += 1
            worksheet.write(row, col, agg['participation_percentage'])

            col += 1
            worksheet.write(row, col, agg['position_avg'])

            row += 1

        # # # 2nd WORKSHEET: XLS AGGS # # #

        worksheet = workbook.add_worksheet()

        headers = [
            'Banner',
            'Imagen',
            'Tienda',
            'Sección',
            'Subsección',
            'Tipo de página',
            'URL subsección',
            'URL de destino',
            self.fields_data[grouping_field]['label'],
            'Participación (puntaje)',
            'Participación (porcentaje)',
            'Posición'
        ]

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1

        for banner_agg in banner_aggs:
            banner = banners_dict[banner_agg['id']]

            col = 0
            worksheet.write(row, col, banner.id)

            col += 1
            worksheet.write_url(row, col, banner.asset.picture_url,
                                string='Imagen', cell_format=url_format)

            col += 1
            worksheet.write(row, col, banner.update.store.name)

            col += 1
            worksheet.write(row, col, banner.subsection.section.name)

            col += 1
            worksheet.write(row, col, banner.subsection.name)

            col += 1
            worksheet.write(row, col, banner.subsection.type.name)

            col += 1
            worksheet.write_url(row, col, banner.url,
                                cell_format=url_format)

            col += 1
            worksheet.write(row, col, banner.destination_urls, url_format)

            col += 1
            worksheet.write(row, col, banner_agg['grouping_label'])

            col += 1
            worksheet.write(row, col, banner_agg['participation_score'])

            col += 1
            worksheet.write(
                row, col,
                (banner_agg['participation_score']*100)/total_participation)

            col += 1
            worksheet.write(row, col, banner.position)

            row += 1

        workbook.close()
        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()

        filename = 'banner_participation.xlsx'

        path = storage.save(filename, file_for_upload)

        return {
            'file': file_value,
            'path': path
        }
