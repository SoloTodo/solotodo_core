import io
from collections import OrderedDict

import xlsxwriter
from django import forms
from django.core.files.base import ContentFile
from django.db.models import Count
from guardian.shortcuts import get_objects_for_user

from solotodo.models import Category, Brand, Store, EntitySectionPosition, \
    StoreSection
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportCurrentEntityPositionsForm(forms.Form):
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
        position_threshold = self.cleaned_data['position_threshold']

        entity_section_positions = EntitySectionPosition.objects.filter(
            entity_history__entity__category__in=categories,
            entity_history__entity__store__in=stores
        ).get_active().select_related(
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
            .order_by('section', 'entity_history__entity__product__brand')\
            .values('section', 'entity_history__entity__product__brand')\
            .annotate(c=Count('*'))

        report_data = {
            (e['section'], e['entity_history__entity__product__brand']): e['c']
            for e in report_raw_data
        }

        # # # REPORT # # #
        output = io.BytesIO()

        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10
        })

        # # # 1st WORKSHEET: AGGREGATED VALUES # # #
        worksheet = workbook.add_worksheet()

        headers = [
            'Tienda',
            'Sección'
        ]

        headers.extend([str(brand) for brand in brands_in_report])

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1

        for section in sections_in_report:
            col = 0
            worksheet.write(row, col, str(section.store))

            col += 1
            worksheet.write(row, col, section.name)

            for brand in brands_in_report:
                col += 1
                worksheet.write(row, col, report_data.get(
                    (section.id, brand.id), 0))

            row += 1

        # # # 2nd WORKSHEET: ORIGINAL DATA # # #

        worksheet = workbook.add_worksheet()

        headers = [
            'Tienda',
            'Sección',
            'Posición',
            'Producto',
            'Categoría',
            'SKU',
            'Nombre en tienda'
        ]

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1

        for entity_section_position in entity_section_positions:
            entity = entity_section_position.entity_history.entity

            col = 0
            worksheet.write(row, col,
                            str(entity_section_position.section.store))

            col += 1
            worksheet.write(row, col, entity_section_position.section.name)

            col += 1
            worksheet.write(row, col, entity_section_position.value)

            col += 1
            worksheet.write(row, col, str(entity.product))

            col += 1
            worksheet.write(row, col, str(entity.category))

            col += 1
            worksheet.write(row, col, entity.sku)

            col += 1
            worksheet.write(row, col, entity.name)

            row += 1

        workbook.close()
        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)
        storage = PrivateS3Boto3Storage()
        filename = 'current_sku_positions.xlsx'
        path = storage.save(filename, file_for_upload)

        return {
            'file': file_value,
            'path': path
        }
