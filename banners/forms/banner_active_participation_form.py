import io
import xlsxwriter
from collections import defaultdict

from django import forms
from django.core.files.base import ContentFile
from django.db.models import F, Avg
from guardian.shortcuts import get_objects_for_user

from solotodo.models import Store, Brand, Category
from solotodo_core.s3utils import PrivateS3Boto3Storage
from banners.models import Banner, BannerSection, BannerSubsectionType

label_getters = {
        'brand': lambda x: x['content'].brand.name,
        'category': lambda x: x['content'].category.name,
        'section': lambda x: x['banner'].subsection.section.name,
        'subsection_type': lambda x: x['banner'].subsection.type.name,
        'type': lambda x: x['banner'].subsection.type.name,
        'store': lambda x: x['banner'].update.store.name}


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

        return banners.distinct()

    def get_common_aggs(self, banners):
        brands = self.cleaned_data['brands']
        categories = self.cleaned_data['categories']

        contents_data = banners.get_contents_data(brands, categories)

        grouping_field = self.cleaned_data['grouping_field']
        db_grouping_field = self.fields_data[grouping_field]['db_name']

        total_participation = 0
        participation_aggs = defaultdict(lambda: 0)
        grouping_labels = []

        for content_data in contents_data:
            total_participation += content_data['content'].percentage
            label = label_getters[grouping_field](content_data)
            if label not in grouping_labels:
                grouping_labels.append(label)
            participation_aggs[label] += content_data['content'].percentage

        position_raw_aggs = banners.order_by(db_grouping_field) \
            .values(db_grouping_field) \
            .annotate(
            grouping_label=F(db_grouping_field + '__name'),
            position_avg=Avg('position'))

        position_aggs = {p['grouping_label']: p['position_avg']
                         for p in position_raw_aggs}

        banner_aggs_result = []

        for label in grouping_labels:
            banner_aggs_result.append({
                'grouping_label': label,
                'participation_score': participation_aggs[label],
                'participation_percentage':
                    participation_aggs[label] * 100 / total_participation,
                'position_avg': position_aggs[label]
            })

        banner_aggs_result = sorted(
            banner_aggs_result, key=lambda x: x['participation_score'],
            reverse=True)

        return banner_aggs_result

    def get_banner_participation_as_json(self):
        banners = self.get_filtered_banners()
        banner_aggs_result = self.get_common_aggs(banners)

        return banner_aggs_result

    def get_banner_participation_as_xls(self):
        brands = self.cleaned_data['brands']
        categories = self.cleaned_data['categories']

        banners = self.get_filtered_banners()\
            .select_related(
            'update__store',
            'subsection__section',
            'subsection__type')

        grouping_field = self.cleaned_data['grouping_field']

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
        contents_data = banners.get_contents_data(brands, categories)
        total_participation = 0

        for content_data in contents_data:
            total_participation += content_data['content'].percentage

        for content_data in contents_data:
            banner = content_data['banner']
            content = content_data['content']
            grouping_label = label_getters[grouping_field](content_data)

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
            worksheet.write(row, col, grouping_label)

            col += 1
            worksheet.write(row, col, content.percentage)

            col += 1
            worksheet.write(
                row, col,
                (content.percentage * 100) / total_participation)

            col += 1
            worksheet.write(row, col, banner.position)

            row += 1

        workbook.close()
        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()

        filename = 'reports/banner_participation.xlsx'

        path = storage.save(filename, file_for_upload)

        return {
            'file': file_value,
            'path': path
        }
