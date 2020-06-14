import io
from collections import defaultdict

import xlsxwriter
from datetime import timedelta

from django import forms
from django.core.files.base import ContentFile
from django.db.models import Count
from django.db.models.functions import ExtractWeek, ExtractYear
from django_filters.fields import IsoDateTimeRangeField
from guardian.shortcuts import get_objects_for_user

from solotodo.models import Category, Brand, EntitySectionPosition, \
    StoreSection
from solotodo.utils import iterable_to_dict
from solotodo_core.s3utils import PrivateS3Boto3Storage


class StoreHistoricEntityPositionsForm(forms.Form):
    timestamp = IsoDateTimeRangeField()
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
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

    def clean_categories(self):
        selected_categories = self.cleaned_data['categories']
        if selected_categories:
            return selected_categories
        else:
            return self.fields['categories'].queryset

    @staticmethod
    def group_entity_section_positions(entity_section_positions, fields):
        conversion_dict = {
            'section': 'section',
            'year': 'year',
            'week': 'week',
            'category': 'entity_history__entity__category',
            'brand': 'entity_history__entity__product__brand'
        }

        converted_fields = [conversion_dict[field] for field in fields]

        result = defaultdict(int)

        for entity_section_position in entity_section_positions:
            key = tuple([entity_section_position[field]
                         for field in converted_fields])
            result[key] += entity_section_position['c']

        return result

    def generate_report(self, store):
        categories = self.cleaned_data['categories']
        brands = self.cleaned_data['brands']
        timestamp = self.cleaned_data['timestamp']
        position_threshold = self.cleaned_data['position_threshold']

        entity_section_positions = EntitySectionPosition.objects.filter(
            entity_history__entity__category__in=categories,
            entity_history__entity__store=store,
            entity_history__entity__product__isnull=False,
            entity_history__timestamp__gte=timestamp.start,
            entity_history__timestamp__lte=timestamp.stop
        ).annotate(
            week=ExtractWeek('entity_history__timestamp'),
            year=ExtractYear('entity_history__timestamp')
        )

        if position_threshold:
            entity_section_positions = entity_section_positions.filter(
                value__lte=position_threshold
            )

        entity_section_positions = entity_section_positions.order_by(
            'section', 'year', 'week',
            'entity_history__entity__category',
            'entity_history__entity__product__brand'
        ).values(
            'section', 'year', 'week',
            'entity_history__entity__category',
            'entity_history__entity__product__brand'
        ).annotate(
            c=Count('*')
        )

        section_year_week_category_data = self.group_entity_section_positions(
            entity_section_positions, ['section', 'year', 'week', 'category'])

        year_week_category_data = self.group_entity_section_positions(
            entity_section_positions, ['year', 'week', 'category'])

        section_year_week_category_brand_data = \
            self.group_entity_section_positions(
                entity_section_positions,
                ['section', 'year', 'week', 'category', 'brand']
            )

        year_week_category_brand_data = self.group_entity_section_positions(
            entity_section_positions, ['year', 'week', 'category', 'brand'])

        category_section_data = self.group_entity_section_positions(
            entity_section_positions, ['category', 'section'])
        sections_per_category = defaultdict(list)

        sections_dict = iterable_to_dict(StoreSection)

        for category_id, section_id in category_section_data.keys():
            sections_per_category[category_id].append(
                sections_dict[section_id])

        category_brand_data = self.group_entity_section_positions(
            entity_section_positions, ['category', 'brand'])
        brands_per_category = defaultdict(list)

        brands_dict = iterable_to_dict(Brand)

        for category_id, brand_id in category_brand_data.keys():
            brands_per_category[category_id].append(
                brands_dict[brand_id])

        iter_date = timestamp.start
        one_week = timedelta(days=7)
        end_year, end_week = timestamp.stop.isocalendar()[:2]
        year_weeks = []

        while True:
            year, week = iter_date.isocalendar()[:2]
            year_weeks.append((year, week))

            if year == end_year and week == end_week:
                break

            iter_date += one_week

        # # # REPORT # # #
        output = io.BytesIO()

        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter'
        })

        percentage_format = workbook.add_format()
        percentage_format.set_num_format('0.00%')
        percentage_format.set_font_size(10)

        percentage_bold_format = workbook.add_format()
        percentage_bold_format.set_num_format('0.00%')
        percentage_bold_format.set_font_size(10)
        percentage_bold_format.set_bold(True)

        # # # Category WORKSHEET # # #
        for category in categories:
            sections_in_category = sections_per_category[category.id]

            if brands:
                brands_in_category = brands
            else:
                brands_in_category = brands_per_category[category.id]

            worksheet = workbook.add_worksheet()
            worksheet.name = category.name

            col = 2

            for year, week in year_weeks:
                if brands_in_category:
                    worksheet.merge_range(
                        0, col,
                        0, col + len(brands_in_category) - 1,
                        '{}-{}'.format(year, week),
                        header_format)
                    col += len(brands_in_category)
                else:
                    worksheet.write(0, col, '{}-{}'.format(year, week))
                    col += 1

            headers = [
                'Tienda',
                'Sección'
            ]

            for year_week in year_weeks:
                headers.extend([str(brand) for brand in brands_in_category])

            for idx, header in enumerate(headers):
                worksheet.write(1, idx, header, header_format)

            row = 2

            for section in sections_in_category:
                col = 0
                worksheet.write(row, col, str(section.store))

                col += 1
                worksheet.write(row, col, section.name)

                for year, week in year_weeks:
                    for brand in brands_in_category:
                        col += 1
                        value = section_year_week_category_brand_data.get(
                            (section.id, year, week, category.id, brand.id), 0)
                        total = section_year_week_category_data.get(
                            (section.id, year, week, category.id), 1)

                        worksheet.write(row, col, value/total,
                                        percentage_format)
                row += 1

            col = 1
            for year, week in year_weeks:
                for brand in brands_in_category:
                    col += 1
                    value = year_week_category_brand_data.get(
                        (year, week, category.id, brand.id), 0)
                    total = year_week_category_data.get(
                        (year, week, category.id), 1)

                    worksheet.write(row, col, value / total,
                                    percentage_bold_format)

        workbook.close()
        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)
        storage = PrivateS3Boto3Storage()
        filename = 'reports/historic_sku_positions.xlsx'
        path = storage.save(filename, file_for_upload)

        return {
            'file': file_value,
            'filename': filename,
            'path': path
        }
