import io
from collections import defaultdict

import xlsxwriter
from django import forms
from django.core.files.base import ContentFile
from django.db.models import Min
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user
from xlsxwriter.utility import xl_rowcol_to_cell

from solotodo.models import Store, Entity
from solotodo_core.s3utils import PrivateS3Boto3Storage
from wtb.models import WtbBrand, WtbEntity


class ReportWtbStorePriceComparisonForm(forms.Form):
    wtb_brand = forms.ModelChoiceField(
        queryset=WtbBrand.objects.all())
    store = forms.ModelChoiceField(
        queryset=Store.objects.all())
    competing_stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all())

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        valid_wtb_brands = get_objects_for_user(user, 'view_wtb_brand',
                                                WtbBrand)
        valid_stores = get_objects_for_user(user, 'view_store_reports', Store)

        self.fields['wtb_brand'].queryset = valid_wtb_brands
        self.fields['store'].queryset = valid_stores
        self.fields['competing_stores'].queryset = valid_stores

    def clean_competing_stores(self):
        selected_stores = self.cleaned_data['competing_stores']
        if selected_stores:
            return selected_stores
        else:
            return self.fields['competing_stores'].queryset

    def generate_report(self):
        wtb_brand = self.cleaned_data['wtb_brand']
        store = self.cleaned_data['store']
        competing_stores = self.cleaned_data['competing_stores']

        wtb_entities = WtbEntity.objects.filter(
            brand=wtb_brand,
            product__isnull=False,
            is_active=True
        ).select_related('product__instance_model', 'category')

        wtb_and_store_entities_per_product = defaultdict(lambda: {
            'wtb_entities': [],
            'store_entities': []
        })

        for wtb_entity in wtb_entities:
            wtb_and_store_entities_per_product[wtb_entity.product][
                'wtb_entities'].append(wtb_entity)

        store_entities = store.entity_set.get_available().filter(
            product__isnull=False,
            condition='https://schema.org/NewCondition'
        ).select_related('product__instance_model')

        for entity in store_entities:
            wtb_and_store_entities_per_product[entity.product][
                'store_entities'].append(entity)

        competing_entities = Entity.objects.get_available().filter(
            store__in=competing_stores,
            seller__isnull=True,
            product__in=wtb_and_store_entities_per_product.keys(),
            active_registry__cell_monthly_payment__isnull=True,
            condition='https://schema.org/NewCondition'
        )

        competing_prices = competing_entities \
            .order_by('product', 'store') \
            .values('product', 'store').annotate(
                price=Min('active_registry__offer_price'))

        product_store_prices_dict = {(x['product'], x['store']): x['price']
                                     for x in competing_prices}

        output = io.BytesIO()

        # Create a workbook and add a worksheet
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)
        worksheet = workbook.add_worksheet()

        currency_format = workbook.add_format({
            'num_format': '#,##0',
            'font_size': 10
        })

        percentage_format = workbook.add_format({
            'num_format': '0.00%',
            'font_size': 10
        })

        header_1_format = workbook.add_format({
            'bg_color': 'navy',
            'font_color': 'white',
            'bold': True,
            'font_size': 10
        })

        header_store_price_format = workbook.add_format({
            'bg_color': 'red',
            'font_color': 'white',
            'bold': True,
            'font_size': 10
        })

        header_competing_stores_format = workbook.add_format({
            'bg_color': 'gray',
            'font_color': 'white',
            'bold': True,
            'font_size': 10
        })

        # Light red fill with dark red text.
        number_bad_format = workbook.add_format({
            'bg_color': '#FFC7CE',
            'font_color': '#9C0006'
        })

        # Light yellow fill with dark yellow text.
        number_neutral_format = workbook.add_format({
            'bg_color': '#FFEB9C',
            'font_color': '#9C6500'
        })

        # Green fill with dark green text.
        number_good_format = workbook.add_format({
            'bg_color': '#C6EFCE',
            'font_color': '#006100'
        })

        data_formulas = [
            '=IFERROR(AVERAGE({stores_range}),"")',
            '=IFERROR((({store_price_cell}-{avg_cell})/{avg_cell}),"")',
            '=IFERROR(MODE({stores_range}), ' +
            'IFERROR(AVERAGE({stores_range}), ""))',
            '=IFERROR((({store_price_cell}-{mode_cell})/{mode_cell}),"")',
            '=IF(MIN({stores_range}), MIN({stores_range}), "")',
            '=IFERROR((({store_price_cell}-{min_cell})/{min_cell}),"")'
        ]

        STARTING_ROW = 0
        STARTING_COL = 0

        row = STARTING_ROW
        col = STARTING_COL
        worksheet.write_string(row, col, 'Categoría', header_1_format)
        worksheet.set_column(col, col, 12)
        col += 1
        worksheet.write_string(row, col, 'Modelo', header_1_format)
        worksheet.set_column(col, col, 24)
        col += 1
        worksheet.write_string(row, col, 'Código LG', header_1_format)
        worksheet.set_column(col, col, 24)
        col += 1
        worksheet.write_string(row, col, 'URL LG', header_1_format)
        worksheet.set_column(col, col, 24)
        col += 1
        worksheet.write_string(row, col, 'Status', header_1_format)
        worksheet.set_column(col, col, 24)
        col += 1
        worksheet.write_string(row, col, 'Precio {}'.format(store),
                               header_store_price_format)
        worksheet.set_column(col, col, 36)
        col += 1
        worksheet.write_string(row, col, 'URL {}'.format(store),
                               header_store_price_format)
        worksheet.set_column(col, col, 36)
        col += 1
        START_RETAILER_COLUMN = col

        for store in competing_stores:
            worksheet.write_string(row, col, str(store),
                                   header_competing_stores_format)
            worksheet.set_column(col, col, 12)
            col += 1

        worksheet.write_string(row, col, 'Average', header_1_format)
        worksheet.set_column(col, col, 10)
        col += 1
        worksheet.write_string(row, col, 'Var. AV.', header_1_format)
        worksheet.set_column(col, col, 10)
        col += 1
        worksheet.write_string(row, col, 'Moda', header_1_format)
        worksheet.set_column(col, col, 10)
        col += 1
        worksheet.write_string(row, col, 'Var. Moda', header_1_format)
        worksheet.set_column(col, col, 10)
        col += 1
        worksheet.write_string(row, col, 'Mínimo', header_1_format)
        worksheet.set_column(col, col, 10)
        col += 1
        worksheet.write_string(row, col, 'Var. Min.', header_1_format)
        worksheet.set_column(col, col, 10)
        col += 1

        row += 1

        for product, wtb_entities_and_store_entities in \
                wtb_and_store_entities_per_product.items():
            wtb_entities = wtb_entities_and_store_entities['wtb_entities'] \
                           or [None]
            store_entities = wtb_entities_and_store_entities['store_entities'] \
                or [None]

            for wtb_e in wtb_entities:
                for store_entity in store_entities:
                    col = STARTING_COL
                    worksheet.write_string(row, col, str(product.category))
                    col += 1
                    worksheet.write_string(row, col, str(product))
                    col += 1
                    worksheet.write_string(
                        row, col, str(wtb_e.model_name
                                      if wtb_e and wtb_e.model_name else 'N/A'))
                    col += 1
                    worksheet.write_string(row, col,
                                           str(wtb_e.url if wtb_e else 'N/A'))
                    col += 1
                    worksheet.write_string(
                        row, col, 'Disponible' if store_entity
                        else 'No disponible')
                    col += 1
                    if store_entity:
                        worksheet.write_number(
                            row, col, store_entity.active_registry.offer_price,
                            currency_format)
                        worksheet.write_string(row, col + 1, store_entity.url,
                                               currency_format)
                    store_price_cell = xl_rowcol_to_cell(row, col)
                    col += 2

                    for store in competing_stores:
                        price = product_store_prices_dict.get(
                            (product.id, store.id), None)
                        if price is not None:
                            worksheet.write_number(row, col, price,
                                                   currency_format)
                        col += 1

                    stores_range = '{}:{}'.format(
                        xl_rowcol_to_cell(row, START_RETAILER_COLUMN),
                        xl_rowcol_to_cell(row, START_RETAILER_COLUMN +
                                          len(competing_stores) - 1),
                    )

                    avg_cell = xl_rowcol_to_cell(row, col)
                    mode_cell = xl_rowcol_to_cell(row, col + 2)
                    min_cell = xl_rowcol_to_cell(row, col + 4)

                    for idx, data_formula in enumerate(data_formulas):
                        formula_cell = xl_rowcol_to_cell(row, col)

                        if 'store_price_cell' in data_formula and not \
                                store_entity:
                            worksheet.write_formula(
                                formula_cell,
                                '=""'
                            )
                        else:
                            number_format = currency_format if idx % 2 == 0 \
                                else percentage_format

                            worksheet.write_formula(
                                formula_cell,
                                data_formula.format(
                                    stores_range=stores_range,
                                    store_price_cell=store_price_cell,
                                    avg_cell=avg_cell,
                                    mode_cell=mode_cell,
                                    min_cell=min_cell
                                ), number_format)
                        col += 1

                    row += 1

        STARTING_DATA_ROW = STARTING_ROW + 1
        ENDING_DATA_ROW = STARTING_DATA_ROW + row - 2
        AVERAGE_VARIATION_COLUMN = START_RETAILER_COLUMN + \
            len(competing_stores) + 1

        for i in [0, 2, 4]:
            target_column = AVERAGE_VARIATION_COLUMN + i
            starting_cell = xl_rowcol_to_cell(STARTING_DATA_ROW, target_column)
            ending_cell = xl_rowcol_to_cell(ENDING_DATA_ROW, target_column)
            cell_range = '{}:{}'.format(starting_cell, ending_cell)
            worksheet.conditional_format(cell_range, {
                'type': 'cell',
                'criteria': 'less than',
                'value': -0.1,
                'format': number_bad_format
            })
            worksheet.conditional_format(cell_range, {
                'type': 'cell',
                'criteria': 'between',
                'minimum': -0.1,
                'maximum': -0.05,
                'format': number_neutral_format
            })
            worksheet.conditional_format(cell_range, {
                'type': 'cell',
                'criteria': 'between',
                'minimum': -0.05,
                'maximum': 0.05,
                'format': number_good_format
            })
            worksheet.conditional_format(cell_range, {
                'type': 'cell',
                'criteria': 'between',
                'minimum': 0.05,
                'maximum': 0.1,
                'format': number_neutral_format
            })
            worksheet.conditional_format(cell_range, {
                'type': 'cell',
                'criteria': 'greater than',
                'value': 0.1,
                'format': number_bad_format
            })

        worksheet.autofilter(0, 0, row - 1, len(competing_stores) + 12)
        workbook.close()

        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()
        filename_template = 'wtb_report_%Y-%m-%d_%H:%M:%S'
        filename = timezone.now().strftime(filename_template)
        path = storage.save('reports/{}.xlsx'.format(filename),
                            file_for_upload)

        print(storage.url(path))

        return {
            'file': file_value,
            'path': path
        }
