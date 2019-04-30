import io

import xlsxwriter
from django import forms
from django.core.files.base import ContentFile
from django.db.models import Count, F
from guardian.shortcuts import get_objects_for_user

from solotodo.models import Category, Brand, EntitySectionPosition, \
    StoreSection
from solotodo_core.s3utils import PrivateS3Boto3Storage


class StoreCurrentEntityPositionsForm(forms.Form):
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

    def generate_report(self, store):
        categories = self.cleaned_data['categories']
        brands = self.cleaned_data['brands']
        position_threshold = self.cleaned_data['position_threshold']

        entity_section_positions = EntitySectionPosition.objects.filter(
            entity_history__entity__category__in=categories,
            entity_history__entity__product__isnull=False,
            entity_history__entity__store=store
        ).get_active().select_related(
            'section__store',
            'entity_history__entity__product__brand',
            'entity_history__entity__product__instance_model',
            'entity_history__entity__category',
            'entity_history__entity__store',
        )

        if position_threshold:
            entity_section_positions = entity_section_positions.filter(
                value__lte=position_threshold
            )

        categories_in_report = Category.objects.filter(pk__in=[
            e['entity_history__entity__category'] for e in
            entity_section_positions
            .order_by('entity_history__entity__category')
            .values('entity_history__entity__category')
        ])

        section_category_raw_data = entity_section_positions \
            .order_by('section', 'entity_history__entity__category') \
            .values('section', 'entity_history__entity__category') \
            .annotate(c=Count('*'))

        section_category_data = {
            (e['section'], e['entity_history__entity__category']): e['c']
            for e in section_category_raw_data
        }

        category_raw_data = entity_section_positions \
            .order_by('entity_history__entity__category') \
            .values('entity_history__entity__category') \
            .annotate(c=Count('*'))

        category_data = {
            (e['entity_history__entity__category']): e['c']
            for e in category_raw_data
        }

        if brands:
            entity_section_positions = entity_section_positions.filter(
                entity_history__entity__product__brand__in=brands
            )

        section_category_brand_raw_data = entity_section_positions\
            .order_by(
                'section', 'entity_history__entity__category',
                'entity_history__entity__product__brand')\
            .values(
                'section', 'entity_history__entity__category',
                'entity_history__entity__product__brand')\
            .annotate(
                c=Count('*'),
            )

        section_category_brand_data = {
            (e['section'], e['entity_history__entity__category'],
             e['entity_history__entity__product__brand']): e['c']
            for e in section_category_brand_raw_data
        }

        category_brand_raw_data = entity_section_positions \
            .order_by(
                'entity_history__entity__category',
                'entity_history__entity__product__brand') \
            .values(
                'entity_history__entity__category',
                'entity_history__entity__product__brand') \
            .annotate(
                c=Count('*'),
            )

        category_brand_data = {
            (e['entity_history__entity__category'],
             e['entity_history__entity__product__brand']): e['c']
            for e in category_brand_raw_data
        }

        # # # REPORT # # #
        output = io.BytesIO()

        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10
        })

        percentage_format = workbook.add_format()
        percentage_format.set_num_format('0.00%')
        percentage_format.set_font_size(10)

        # # # 1st WORKSHEET: AGGREGATED VALUES # # #
        for category in categories_in_report:
            entity_section_positions_in_category = entity_section_positions\
                .filter(entity_history__entity__category=category)

            sections_in_category = StoreSection.objects.filter(
                pk__in=[e['section'] for e in
                        entity_section_positions_in_category
                        .order_by('section')
                        .values('section')])\
                .select_related('store')

            if brands:
                brands_in_category = brands
            else:
                brands_in_category = Brand.objects.filter(
                    pk__in=[e['entity_history__entity__product__brand']
                            for e in entity_section_positions_in_category
                            .order_by('entity_history__entity__product__brand')
                            .values('entity_history__entity__product__brand')])

            worksheet = workbook.add_worksheet()
            worksheet.name = category.name

            headers = [
                'Tienda',
                'Sección'
            ]

            brand_headers = [str(brand) for brand in brands_in_category]

            for idx, header in enumerate(headers):
                worksheet.write(0, idx, header, header_format)

            for idx, header in enumerate(brand_headers):
                worksheet.write(0, (idx+1)*2, header, header_format)

            row = 1

            for section in sections_in_category:
                col = 0
                worksheet.write(row, col, str(section.store))

                col += 1
                worksheet.write(row, col, section.name)

                for brand in brands_in_category:
                    col += 1
                    value = section_category_brand_data.get(
                        (section.id, category.id, brand.id), 0) / \
                        section_category_data.get(
                        (section.id, category.id), 1)
                    worksheet.write(row, col,section_category_brand_data.get(
                        (section.id, category.id, brand.id), 0))
                    col += 1
                    worksheet.write(row, col, value, percentage_format)

                worksheet.write(row, col, section_category_data.get(
                    (section.id, category.id), 0))

                row += 1

            col = 1
            for brand in brands_in_category:
                col += 1
                value = category_brand_data.get((category.id, brand.id), 0) / \
                    category_data.get(category.id, 1)

                worksheet.write(row, (col*2)-1, value, percentage_format)

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
