import io
import xlsxwriter
from datetime import timedelta

from django import forms
from django.core.files.base import ContentFile
from django.db.models import Count
from django.db.models.functions import ExtractWeek, ExtractYear
from guardian.shortcuts import get_objects_for_user

from solotodo.filter_utils import IsoDateTimeRangeField
from solotodo.models import Category, Brand, Store, EntitySectionPosition, \
    StoreSection
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportHistoricEntityPositionsForm(forms.Form):
    timestamp = IsoDateTimeRangeField()
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False
    )
    stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all(),
        required=False
    )
    brands = forms.ModelMultipleChoiceField(
        queryset=Brand.objects.all(),
        required=False
    )
    position_threshold = forms.IntegerField(
        required=False
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        valid_categories = get_objects_for_user(
            user, 'view_category_entity_positions', Category)
        self.fields['categories'].queryset = valid_categories

        valid_stores = get_objects_for_user(
            user, 'view_store_entity_positions', Store)
        self.fields['stores'].queryset = valid_stores

    def clean_categories(self):
        selected_categories = self.cleaned_data['categories']
        if selected_categories:
            return selected_categories
        else:
            return self.fields['categories'].queryset

    def clean_stores(self):
        selected_stores = self.cleaned_data['stores']
        if selected_stores:
            return selected_stores
        else:
            return self.fields['stores'].queryset

    def generate_report(self):
        categories = self.cleaned_data['categories']
        stores = self.cleaned_data['stores']
        brands = self.cleaned_data['brands']
        timestamp = self.cleaned_data['timestamp']
        position_threshold = self.cleaned_data['position_threshold']

        entity_section_positions = EntitySectionPosition.objects.filter(
            entity_history__entity__category__in=categories,
            entity_history__entity__store__in=stores,
            entity_history__timestamp__gte=timestamp.start,
            entity_history__timestamp__lte=timestamp.stop
        ).select_related(
            'section__store',
            'entity_history__entity__product__brand',
            'entity_history__entity__product__instance_model',
            'entity_history__entity__category',
            'entity_history__entity__store',
        )

        if brands:
            entity_section_positions = entity_section_positions.filter(
                entity_history__entity__product__brand__in=brands
            )
        else:
            entity_section_positions = entity_section_positions.filter(
                entity_history__entity__product__isnull=False
            )

        if position_threshold:
            entity_section_positions = entity_section_positions.filter(
                value__lte=position_threshold
            )

        sections_in_report = StoreSection.objects.filter(pk__in=[
            e['section'] for e in entity_section_positions.order_by(
                'section').values('section')
        ]).select_related('store')

        brands_in_report = Brand.objects.filter(pk__in=[
            e['entity_history__entity__product__brand'] for e in
            entity_section_positions
                .order_by('entity_history__entity__product__brand')
                .values('entity_history__entity__product__brand')
        ])

        report_raw_data = entity_section_positions\
            .order_by(
                'entity_history', 'section',
                'entity_history__entity__product__brand')\
            .values(
                'entity_history', 'section',
                'entity_history__entity__product__brand') \
            .annotate(
                c=Count('*'),
                week=ExtractWeek('entity_history__timestamp'),
                year=ExtractYear('entity_history__timestamp')
            )

        report_data = {}

        for data in report_raw_data:
            year_week = '{}-{}'. format(data['year'], data['week'])
            section = data['section']
            brand = data['entity_history__entity__product__brand']
            if (year_week, section, brand) not in report_data:
                report_data[(year_week, section, brand)] = []

            report_data[(year_week, section, brand)].append(data['c'])

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

        # # # REPORT # # #
        output = io.BytesIO()

        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10
        })

        # # # 1st WORKSHEET # # #
        worksheet = workbook.add_worksheet()

        headers = [
            'Tienda',
            'Sección'
        ]

        for year_week in year_weeks:
            headers.extend([str(brand) for brand in brands_in_report])

        for idx, header in enumerate(headers):
            worksheet.write(1, idx, header, header_format)

        row = 2

        for section in sections_in_report:
            col = 0
            worksheet.write(row, col, str(section.store))

            col += 1
            worksheet.write(row, col, section.name)

            for year_week in year_weeks:
                for brand in brands_in_report:
                    col +=1
                    positions = report_data.get(
                        (year_week, section.id, brand.id), [0])
                    worksheet.write(row, col, sum(positions)/len(positions))

            row += 1

        workbook.close()
        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)
        storage = PrivateS3Boto3Storage()
        filename = 'historic_sku_positions.xlsx'
        path = storage.save(filename, file_for_upload)

        return {
            'file': file_value,
            'path': path
        }
