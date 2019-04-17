import io
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell
from collections import defaultdict
from datetime import timedelta

from django import forms

from django.db.models import F, Sum, Avg, Count
from django.db.models.functions import ExtractWeek, ExtractYear
from django.core.files.base import ContentFile
from guardian.shortcuts import get_objects_for_user

from solotodo.filter_utils import IsoDateTimeRangeField
from solotodo.models import Store, Brand, Category
from solotodo_core.s3utils import PrivateS3Boto3Storage
from banners.models import Banner, BannerSection, BannerSubsectionType


class BannerHistoricParticipationForm(forms.Form):
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
    timestamp = IsoDateTimeRangeField()
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
        timestamp = self.cleaned_data['timestamp']

        banners = Banner.objects.filter(
            asset__contents__percentage__isnull=False,
            update__timestamp__gte=timestamp.start,
            update__timestamp__lte=timestamp.stop
        ).annotate(
            week=ExtractWeek('update__timestamp'),
            year=ExtractYear('update__timestamp')
        ).prefetch_related(
            'asset__contents__brand',
            'asset__contents__category',
        ).select_related(
            'update__store',
            'subsection__section'
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

        return banners.distinct().order_by('id')

    def get_data(self):
        banners = self.get_filtered_banners()

        grouping_field = self.cleaned_data['grouping_field']
        db_grouping_field = self.fields_data[grouping_field]['db_name']

        store_updates = banners.order_by('year', 'week', 'update__store')\
            .values('year', 'week', 'update__store__name').distinct()\
            .annotate(update_count=Count('update', distinct=True))

        store_updates = {
            ('{}-{}'.format(s['year'], s['week']), s['update__store__name']):
                s['update_count']
            for s in store_updates
        }

        participation_aggs = banners\
            .order_by('year', 'week', 'update__store', db_grouping_field)\
            .values('year', 'week', 'update__store__name', db_grouping_field)\
            .annotate(
                grouping_label=F(db_grouping_field + '__name'),
                participation_score=Sum('asset__contents__percentage'))\
            .order_by('grouping_label')

        position_aggs = banners\
            .order_by('year', 'week', db_grouping_field)\
            .values('year', 'week', db_grouping_field)\
            .annotate(
                grouping_label=F(db_grouping_field + '__name'),
                position_avg=Avg('position'))\
            .order_by('grouping_label')

        contents_data = []

        for banner in banners:
            asset = banner.asset
            for content in asset.contents.all():
                if grouping_field in ['brand', 'category']:
                    grouping_label = getattr(
                        content, grouping_field).name
                elif grouping_field in ['section', 'subsection_type', 'type']:
                    if grouping_field == 'subsection_type':
                        grouping_field = 'type'

                    grouping_label = getattr(
                        banner.subsection, grouping_field).name
                else:
                    grouping_label = getattr(
                        banner.update, grouping_field).name

                contents_data.append({
                    'banner': banner,
                    'content': content,
                    'grouping_label': grouping_label})

        banner_aggs_result = defaultdict(lambda: {'participation_score': 0})
        year_week_participation = defaultdict(lambda: 0)

        for agg in participation_aggs:
            year_week = '{}-{}'.format(agg['year'], agg['week'])
            grouping_label = agg['grouping_label']
            store_name = agg['update__store__name']

            year_week_store_update_count = \
                store_updates[(year_week, store_name)]
            normalized_store_participation_score = \
                agg['participation_score'] / year_week_store_update_count

            banner_aggs_result[(year_week, grouping_label)][
                'participation_score'] += normalized_store_participation_score

            year_week_participation[year_week] += \
                normalized_store_participation_score

        for agg in position_aggs:
            year_week = '{}-{}'.format(agg['year'], agg['week'])
            grouping_label = agg['grouping_label']

            banner_aggs_result[(year_week, grouping_label)][
                'position_avg'] = agg['position_avg']

        return {
            'aggs': banner_aggs_result,
            'year_week_participation': year_week_participation,
            'contents_data': contents_data,
            'store_updates': store_updates
        }

    def generate_report(self):
        timestamp = self.cleaned_data['timestamp']
        grouping_field = self.cleaned_data['grouping_field']

        data = self.get_data()
        aggs = data['aggs']
        year_week_participation = data['year_week_participation']

        iter_date = timestamp.start
        one_week = timedelta(days=7)
        end_year, end_week = timestamp.stop.isocalendar()[:2]
        year_weeks = []

        while True:
            year, week = iter_date.isocalendar()[:2]
            year_weeks.append('{}-{}'.format(year, week))

            if year == end_year and week == end_week:
                break

            iter_date += one_week

        groups_and_year_weeks = aggs.keys()
        groups_values = set()

        for group_and_year_week in groups_and_year_weeks:
            groups_values.add(group_and_year_week[1])

        groups_values = list(groups_values)
        groups_values.sort()

        output = io.BytesIO()

        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)
        workbook.remove_timezone = True

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10
        })

        decimal_format = workbook.add_format()
        decimal_format.set_num_format('0.00')
        decimal_format.set_font_size(10)

        percentage_format = workbook.add_format()
        percentage_format.set_num_format('0.00%')
        percentage_format.set_font_size(10)

        datetime_format = workbook.add_format()
        datetime_format.set_num_format('yyyy-mm-dd hh:mm')
        datetime_format.set_font_size(10)

        url_format = workbook.add_format()
        url_format.set_font_size(10)

        headers = [
            self.fields_data[grouping_field]['label']
        ]

        for year_week in year_weeks:
            headers.append(year_week)

        default_value = {
            'participation_score': 0,
            'participation_percentage': 0,
            'position_avg': 0
        }

        score_worksheet = workbook.add_worksheet()
        score_worksheet.name = 'Participación (puntaje)'

        percentage_worksheet = workbook.add_worksheet()
        percentage_worksheet.name = 'Participación (%)'

        position_worksheet = workbook.add_worksheet()
        position_worksheet.name = 'Posición promedio'

        for idx, header in enumerate(headers):
            score_worksheet.write(0, idx, header, header_format)
            percentage_worksheet.write(0, idx, header, header_format)
            position_worksheet.write(0, idx, header, header_format)

        row = 1

        for group_value in groups_values:
            col = 0
            score_worksheet.write(row, col, group_value)
            percentage_worksheet.write(row, col, group_value)
            position_worksheet.write(row, col, group_value)
            col += 1
            for year_week in year_weeks:
                value = aggs.get((year_week, group_value), default_value)
                participation = year_week_participation.get(year_week, 1)
                score_worksheet.write(row, col, value['participation_score'],
                                      decimal_format)
                percentage_worksheet.write(
                    row, col, value['participation_score']/participation,
                    percentage_format)
                position_worksheet.write(row, col, value['position_avg'],
                                         decimal_format)
                col += 1
            row += 1

        contents_worksheet = workbook.add_worksheet()
        contents_worksheet.name = 'Datos'

        contents_data = data['contents_data']
        store_updates = data['store_updates']

        content_headers = [
            'Tienda',
            'Contenido',
            'Fecha',
            'Semana',
            'Subsección',
            self.fields_data[grouping_field]['label'],
            'Marca',
            'Categoría',
            'Posición',
            'Puntaje',
            'Cantidad actualizaciones de tienda',
            'Puntaje normalizado'
        ]

        for idx, header in enumerate(content_headers):
            contents_worksheet.write(0, idx, header, header_format)

        row = 1

        for content_data in contents_data:
            banner = content_data['banner']
            content = content_data['content']
            grouping_label = content_data['grouping_label']
            year_week = '{}-{}'.format(banner.year, banner.week)
            store_name = banner.update.store.name

            col = 0
            contents_worksheet.write(row, col, store_name)

            col += 1
            contents_worksheet.write_url(
                row, col, banner.asset.picture_url, url_format,
                string='Imagen {}'.format(banner.asset.id))

            col += 1
            contents_worksheet.write_datetime(
                row, col, banner.update.timestamp, datetime_format)

            col += 1
            contents_worksheet.write(row, col, year_week)

            col += 1
            contents_worksheet.write_url(
                row, col, banner.url, url_format,
                string='{} > {}'.format(
                    banner.subsection.section.name, banner.subsection.name))

            col += 1
            contents_worksheet.write(row, col, grouping_label)

            col += 1
            contents_worksheet.write(row, col, content.brand.name)

            col += 1
            contents_worksheet.write(row, col, content.category.name)

            col += 1
            contents_worksheet.write(row, col, banner.position)

            col += 1
            contents_worksheet.write(row, col, content.percentage)

            col += 1
            contents_worksheet.write(row, col,
                                     store_updates[(year_week, store_name)])

            col += 1
            score_cell = xl_rowcol_to_cell(row, col-2)
            updates_cell = xl_rowcol_to_cell(row, col-1)
            normalized_cell = xl_rowcol_to_cell(row, col)
            formula = '={}/{}'.format(score_cell, updates_cell)

            contents_worksheet.write_formula(normalized_cell, formula,
                                             decimal_format)

            row += 1

        workbook.close()

        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)
        storage = PrivateS3Boto3Storage()
        filename = 'banner_historic_participation.xlsx'
        path = storage.save(filename, file_for_upload)

        return {
            'file': file_value,
            'path': path
        }
