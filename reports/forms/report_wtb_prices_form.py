import io

import xlsxwriter
from django import forms
from django.core.files.base import ContentFile
from django.db.models import Min
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user
from xlsxwriter.utility import xl_rowcol_to_cell

from wtb.models import WtbBrand, WtbEntity
from solotodo.models import Store, Entity
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportWtbPricesForm(forms.Form):
    wtb_brand = forms.ModelChoiceField(
        queryset=WtbBrand.objects.all())
    stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all(),
        required=False)
    price_type = forms.ChoiceField(
        choices=[
            ('normal_price', 'Normal price'),
            ('offer_price', 'Offer price'),
        ]
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        valid_wtb_brands = get_objects_for_user(user, 'view_wtb_brand',
                                                WtbBrand)
        self.fields['wtb_brand'].queryset = valid_wtb_brands

        valid_stores = get_objects_for_user(user, 'view_store_reports', Store)
        self.fields['stores'].queryset = valid_stores

    def clean_stores(self):
        selected_stores = self.cleaned_data['stores']
        if selected_stores:
            return selected_stores
        else:
            return self.fields['stores'].queryset

    def generate_report(self):
        wtb_brand = self.cleaned_data['wtb_brand']
        stores = self.cleaned_data['stores']

        wtb_entities = WtbEntity.objects.filter(
            brand=wtb_brand, product__isnull=False, is_active=True,
            price__isnull=False).select_related(
            'product__instance_model', 'category')

        product_ids = [wtb_e.product_id for wtb_e in wtb_entities]

        prices = Entity.objects.get_available().filter(
            store__in=stores,
            product__in=product_ids,
            active_registry__cell_monthly_payment__isnull=True,
            condition='https://schema.org/NewCondition'
        ).order_by('product', 'store').values('product', 'store').annotate(
            price=Min('active_registry__{}'.format(
                self.cleaned_data['price_type'])))
        product_store_prices_dict = {(x['product'], x['store']): x['price']
                                     for x in prices}

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

        header_wtb_price_format = workbook.add_format({
            'bg_color': 'red',
            'font_color': 'white',
            'bold': True,
            'font_size': 10
        })

        header_store_format = workbook.add_format({
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
            '=+IFERROR(AVERAGE({stores_range}),"")',
            '=+IFERROR((({wtb_price_cell}-{avg_cell})/{avg_cell}),"")',
            '=IFERROR(MODE({stores_range}), ' +
            'IFERROR(AVERAGE({stores_range}), ""))',
            '=+IFERROR((({wtb_price_cell}-{mode_cell})/{mode_cell}),"")',
            '=+IFERROR(MIN({stores_range}),"")',
            '=+IFERROR((({wtb_price_cell}-{min_cell})/{min_cell}),"")'
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
        worksheet.write_string(row, col, 'Precio LG.com',
                               header_wtb_price_format)
        worksheet.set_column(col, col, 16)

        col += 1

        for store in stores:
            worksheet.write_string(row, col, str(store), header_store_format)
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

        for wtb_e in wtb_entities:
            col = STARTING_COL
            worksheet.write_string(row, col, str(wtb_e.category))
            col += 1
            worksheet.write_string(row, col, str(wtb_e.product))
            col += 1
            worksheet.write_number(row, col, wtb_e.price, currency_format)
            wtb_price_cell = xl_rowcol_to_cell(row, col)
            col += 1

            for store in stores:
                price = product_store_prices_dict.get(
                    (wtb_e.product_id, store.id), None)
                if price is not None:
                    worksheet.write_number(row, col, price, currency_format)
                col += 1

            stores_range = '{}:{}'.format(
                xl_rowcol_to_cell(row, STARTING_COL + 3),
                xl_rowcol_to_cell(row, STARTING_COL + 3 + len(stores) - 1),
            )

            avg_cell = xl_rowcol_to_cell(row, col)
            mode_cell = xl_rowcol_to_cell(row, col + 2)
            min_cell = xl_rowcol_to_cell(row, col + 4)

            for idx, data_formula in enumerate(data_formulas):
                number_format = currency_format if idx % 2 == 0 \
                    else percentage_format

                formula_cell = xl_rowcol_to_cell(row, col)
                worksheet.write_formula(
                    formula_cell,
                    data_formula.format(
                        stores_range=stores_range,
                        wtb_price_cell=wtb_price_cell,
                        avg_cell=avg_cell,
                        mode_cell=mode_cell,
                        min_cell=min_cell
                    ), number_format)
                col += 1

            row += 1

        STARTING_DATA_ROW = STARTING_ROW + 1
        ENDING_DATA_ROW = STARTING_DATA_ROW + len(wtb_entities) - 1
        AVERAGE_VARIATION_COLUMN = STARTING_COL + 3 + len(stores) + 1

        for i in [0, 2, 4]:
            target_column = AVERAGE_VARIATION_COLUMN + i
            starting_cell = xl_rowcol_to_cell(STARTING_DATA_ROW, target_column)
            ending_cell = xl_rowcol_to_cell(ENDING_DATA_ROW, target_column)
            cell_range = '{}:{}'.format(starting_cell, ending_cell)
            worksheet.conditional_format(cell_range, {
                'type': 'cell',
                'criteria': 'greater than',
                'value': 0.1,
                'format': number_bad_format
            })
            worksheet.conditional_format(cell_range, {
                'type': 'cell',
                'criteria': 'between',
                'minimum':  0.05,
                'maximum':  0.1,
                'format': number_neutral_format
            })
            worksheet.conditional_format(cell_range, {
                'type': 'cell',
                'criteria': 'less than',
                'value': 0.05,
                'format': number_good_format
            })

        worksheet.autofilter(0, 0, row - 1, len(stores) + 8)
        workbook.close()

        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()
        filename_template = 'wtb_report_%Y-%m-%d_%H:%M:%S'
        filename = timezone.now().strftime(filename_template)
        path = storage.save('reports/{}.xlsx'.format(filename),
                            file_for_upload)

        return {
            'file': file_value,
            'path': path
        }
