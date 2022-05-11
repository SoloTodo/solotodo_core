import io
import xlsxwriter
from django.db.models import Min
from xlsxwriter.utility import xl_rowcol_to_cell

from django.db import models
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model

from solotodo.models import Brand, Store, Category, Entity, Product, Currency
from solotodo_core.s3utils import PrivateS3Boto3Storage


class BrandComparison(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    name = models.CharField(max_length=512)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand_1 = models.ForeignKey(Brand, on_delete=models.CASCADE,
                                related_name='+')
    brand_2 = models.ForeignKey(Brand, on_delete=models.CASCADE,
                                related_name='+')
    price_type = models.CharField(
        max_length=512,
        choices=[('normal', 'Normal'), ('offer', 'Offer')],
        default='offer')
    stores = models.ManyToManyField(Store)
    manual_products = models.ManyToManyField(Product)

    def add_segment(self, name):
        from .brand_comparison_segment import BrandComparisonSegment
        from .brand_comparison_segment_row import BrandComparisonSegmentRow
        last_segment = self.segments.last()

        if last_segment:
            next_ordering = last_segment.ordering + 1
        else:
            next_ordering = 1

        segment = BrandComparisonSegment.objects.create(
            name=name,
            ordering=next_ordering,
            comparison=self)

        BrandComparisonSegmentRow.objects.create(
            ordering=1,
            segment=segment)

    def add_manual_product(self, product_id):
        product = Product.objects.get(id=product_id)
        self.manual_products.add(product)

    def remove_manual_product(self, product_id):
        product = Product.objects.get(id=product_id)
        self.manual_products.remove(product)

    def as_xls(self, report_format='1'):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        if report_format == '1':
            self.as_worksheet(workbook)
            self.as_worksheet_2(workbook, highlight_prices=True)
        elif report_format == '2':
            self.as_worksheet_2(workbook, highlight_prices=False)
        else:
            raise Exception('Invalid report format')

        workbook.close()
        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)
        storage = PrivateS3Boto3Storage()
        filename = 'brand_comparison.xlsx'
        path = storage.save(filename, file_for_upload)

        return {
            'file': file_value,
            'path': path
        }

    def as_worksheet_2(self, workbook, highlight_prices=False):
        stores = self.stores.all()

        # Put Falabella, Ripley and Paris first, this is just hardcoded because
        # LG are the only ones using this report right now, if a new customer
        # starts using it then move this functionality to DB level.
        retailer_a_priority = {
            9: 1,
            18: 2,
            11: 3,
            43: 4
        }
        stores = sorted(stores,
                        key=lambda x: retailer_a_priority.get(x.id, 999))

        preferred_currency = Currency.objects.get(iso_code='CLP')
        relevant_product_ids = []
        pricing_row_count = 0
        for segment in self.segments.prefetch_related('rows'):
            for row in segment.rows.all():
                pricing_row_count += 1
                if row.product_1_id:
                    relevant_product_ids.append(row.product_1_id)
                if row.product_2_id:
                    relevant_product_ids.append(row.product_2_id)

        es = Entity.objects.filter(
            store__in=stores,
            product__in=relevant_product_ids,
            seller__isnull=True
        ).get_available()\
            .order_by('store', 'product')\
            .values('store', 'product')\
            .annotate(price=Min('active_registry__{}_price'.format(
                self.price_type)))

        store_product_price_dict = {(x['store'], x['product']): x['price']
                                    for x in es}

        worksheet = workbook.add_worksheet()

        # Styling
        store_header_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bold': True,
            'align': 'center',
            'bg_color': '#F2F1F0',
            'left': 1,
            'right': 1,
            'bottom': 1,
        })

        table_hardcoded_header_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bold': True,
            'align': 'center',
            'bg_color': '#F2F1F0',
            'bottom': 1,
        })

        table_brand_1_header_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bold': True,
            'align': 'center',
            'bg_color': '#F2F1F0',
            'bottom': 1,
            'left': 1
        })

        table_brand_2_header_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bold': True,
            'align': 'center',
            'bg_color': '#F2F1F0',
            'bottom': 1,
            'right': 1
        })

        segment_label_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bottom': 1,
        })

        product_label_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': '#F2F1F0'
        })

        bottom_product_label_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': '#F2F1F0',
            'bottom': 1
        })

        highlighted_product_1_label_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': '#d99694'
        })

        highlighted_bottom_product_1_label_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': '#d99694',
            'bottom': 1
        })

        highlighted_product_2_label_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': '#95b3d7'
        })

        highlighted_bottom_product_2_label_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': '#95b3d7',
            'bottom': 1
        })

        price_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': 'white',
        })
        price_format.set_num_format(preferred_currency.excel_format())

        number_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': 'white',
            'num_format': '0_);[RED]\(0\)'
        })

        bottom_price_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': 'white',
            'bottom': 1
        })
        bottom_price_format.set_num_format(preferred_currency.excel_format())

        bottom_number_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': 'white',
            'bottom': 1,
            'num_format': '0_);[RED]\(0\)'
        })

        brand_1_price_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': 'white',
            'left': 1
        })
        brand_1_price_format.set_num_format(preferred_currency.excel_format())

        bottom_brand_1_price_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': 'white',
            'left': 1,
            'bottom': 1
        })
        bottom_brand_1_price_format.set_num_format(
            preferred_currency.excel_format())

        brand_2_price_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': 'white',
            'right': 1
        })
        brand_2_price_format.set_num_format(preferred_currency.excel_format())

        bottom_brand_2_price_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': 'white',
            'right': 1,
            'bottom': 1
        })
        bottom_brand_2_price_format.set_num_format(
            preferred_currency.excel_format())

        highlight_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': '#66FFCC',
        })

        # Column widths
        worksheet.set_column(0, 0, 12)
        worksheet.set_column(1, 1, 16)
        worksheet.set_column(2, 2, 12)
        worksheet.set_column(5, 5, 16)
        worksheet.set_column(6, 6, 12)

        PRICING_DETAIL_START_COLUMN = 7
        row = 0
        retailer_a_columns = []

        # First row, print store labels
        col = PRICING_DETAIL_START_COLUMN

        for store in stores:
            worksheet.merge_range(row, col, row, col + 1,
                                  str(store), cell_format=store_header_format)

            if store.id in retailer_a_priority:
                retailer_a_columns.append(col)

            col += 2

        # Print a final column for the averages of Retail A
        worksheet.merge_range(row, col, row, col + 1,
                              "Retail A", cell_format=store_header_format)

        row += 1

        # Second row, table titles
        col = 0
        hardcoded_titles = [
            'Category',
            str(self.brand_1), 'Mínimo Retail A',
            'Line Logic', 'ATA',
            str(self.brand_2), 'Mínimo Retail A'
        ]

        for title in hardcoded_titles:
            worksheet.write(row, col, title, table_hardcoded_header_format)
            col += 1

        # We print an additional column ("+1") for the Retail A averages
        for idx in range(len(stores) + 1):
            worksheet.write(row, col, str(self.brand_1),
                            table_brand_1_header_format)
            col += 1
            worksheet.write(row, col, str(self.brand_2),
                            table_brand_2_header_format)
            col += 1

        row += 1

        # ATA label column
        ata_row = row
        for segment in self.segments.prefetch_related('rows'):
            segment_length = segment.rows.count()
            worksheet.merge_range(ata_row, 0, ata_row + segment_length - 1, 0,
                                  str(segment.name),
                                  cell_format=segment_label_format)
            ata_row += segment_length

        # Individual product rows
        data_formulas = [
            '=IFERROR(MIN({}), "")',
        ]

        for segment in self.segments.prefetch_related(
                'rows__product_1', 'rows__product_2'):
            segment_size = segment.rows.count()
            for product_row_idx, product_row in enumerate(segment.rows.all()):
                brand_1_cells = []
                brand_2_cells = []

                brand_1_retailer_a_cells = [
                    xl_rowcol_to_cell(row, retailer_a_col)
                    for retailer_a_col in retailer_a_columns
                ]

                brand_2_retailer_a_cells = [
                    xl_rowcol_to_cell(row, retailer_a_col + 1)
                    for retailer_a_col in retailer_a_columns
                ]

                for idx, store in enumerate(stores):
                    brand_1_cells.append(
                        xl_rowcol_to_cell(
                            row, PRICING_DETAIL_START_COLUMN + 2 * idx))
                    brand_2_cells.append(
                        xl_rowcol_to_cell(
                            row, PRICING_DETAIL_START_COLUMN + 2 * idx + 1))

                is_last_of_segment = (product_row_idx == segment_size - 1)
                if is_last_of_segment:
                    product_label_format_to_use = bottom_product_label_format
                    highlighted_product_1_label_format_to_use = \
                        highlighted_bottom_product_1_label_format
                    highlighted_product_2_label_format_to_use = \
                        highlighted_bottom_product_2_label_format
                    price_format_to_use = bottom_price_format
                    number_format_to_use = bottom_number_format
                    brand_1_price_format_to_use = bottom_brand_1_price_format
                    brand_2_price_format_to_use = bottom_brand_2_price_format
                else:
                    product_label_format_to_use = product_label_format
                    highlighted_product_1_label_format_to_use = \
                        highlighted_product_1_label_format
                    highlighted_product_2_label_format_to_use = \
                        highlighted_product_2_label_format
                    price_format_to_use = price_format
                    number_format_to_use = number_format
                    brand_1_price_format_to_use = brand_1_price_format
                    brand_2_price_format_to_use = brand_2_price_format

                col = 1
                product_1 = product_row.product_1
                if product_1:
                    cell_style = highlighted_product_1_label_format_to_use \
                        if product_row.is_product_1_highlighted \
                        else product_label_format_to_use
                    worksheet.write(row, col, str(product_1), cell_style)
                else:
                    worksheet.write(row, col, '', product_label_format_to_use)

                col += 1

                for data_formula in data_formulas:
                    formula_cell = xl_rowcol_to_cell(row, col)

                    worksheet.write_formula(
                        formula_cell, data_formula.format(
                            ','.join(brand_1_retailer_a_cells)),
                        price_format_to_use)
                    col += 1

                worksheet.write_number(row, col, 0, number_format_to_use)
                col += 1

                worksheet.write_formula(
                    xl_rowcol_to_cell(row, col),
                    '=IFERROR({}/({}+{})*100,"-")'.format(
                        xl_rowcol_to_cell(row, col-2),
                        xl_rowcol_to_cell(row, col+2),
                        xl_rowcol_to_cell(row, col-1),
                    ),
                    number_format_to_use
                )
                col += 1

                product_2 = product_row.product_2
                if product_2:
                    cell_style = highlighted_product_2_label_format_to_use \
                        if product_row.is_product_2_highlighted \
                        else product_label_format_to_use
                    worksheet.write(row, col, str(product_2), cell_style)
                else:
                    worksheet.write(row, col, '', product_label_format_to_use)

                col += 1

                for data_formula in data_formulas:
                    formula_cell = xl_rowcol_to_cell(row, col)
                    worksheet.write_formula(
                        formula_cell, data_formula.format(
                            ','.join(brand_2_retailer_a_cells)),
                        price_format_to_use)
                    col += 1

                brand_1_cells_with_prices = []
                brand_2_cells_with_prices = []

                for store in stores:
                    product_1_price = None
                    if product_1:
                        product_1_price = store_product_price_dict.get(
                            (store.id, product_1.id), None)
                        if product_1_price:
                            brand_1_cells_with_prices.append(
                                xl_rowcol_to_cell(row, col))

                    worksheet.write(row, col, product_1_price,
                                    brand_1_price_format_to_use)
                    col += 1

                    product_2_price = None
                    if product_2:
                        product_2_price = store_product_price_dict.get(
                            (store.id, product_2.id), None)
                        if product_2_price:
                            brand_2_cells_with_prices.append(
                                xl_rowcol_to_cell(row, col))

                    worksheet.write(row, col, product_2_price,
                                    brand_2_price_format_to_use)
                    col += 1

                if highlight_prices:
                    for brand_cells_with_prices in [brand_1_cells_with_prices,
                                                    brand_2_cells_with_prices]:
                        if not brand_cells_with_prices:
                            continue

                        formula = 'MIN({})'.format(','.join(
                            brand_cells_with_prices))
                        for cell in brand_cells_with_prices:
                            worksheet.conditional_format(
                                cell,
                                {
                                    'type': 'cell',
                                    'criteria': '=',
                                    'value': formula,
                                    'format': highlight_format
                                }
                            )

                # Last column for Retailer A average
                retailer_a_base_formula = '=IFERROR(AVERAGEA({}), "-")'

                worksheet.write_formula(
                    xl_rowcol_to_cell(row, col),
                    retailer_a_base_formula.format(
                        ','.join(brand_1_retailer_a_cells)),
                    brand_1_price_format_to_use)
                col += 1

                worksheet.write_formula(
                    xl_rowcol_to_cell(row, col),
                    retailer_a_base_formula.format(
                        ','.join(brand_2_retailer_a_cells)),
                    brand_2_price_format_to_use)
                col += 1

                row += 1

    def as_worksheet(self, workbook):
        preferred_currency = self.user.preferred_currency

        workbook.formats[0].set_font_size(10)

        header_format = workbook.add_format({
            'bold': True,
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#F2F1F0',
            'bottom': 1,
        })

        product_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#F2F1F0',
        })

        ata_format = workbook.add_format({
            'bold': True,
            'font_name': 'Arial Narrow',
            'font_size': 11,
            'align': 'center',
            'valign': 'vcenter',
            'bottom': 1,
        })

        bottom_currency_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': 'white',
            'bottom': 1,
        })
        bottom_currency_format.set_num_format(
            preferred_currency.excel_format())

        bottom_product_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#F2F1F0',
            'bottom': 1,
        })

        highlight_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': '#66FFCC',
        })

        product_1_highlight_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#d99694',
        })

        product_2_highlight_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#95b3d7',
        })

        blanks_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': 'white',
        })

        currency_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': 'white',
        })
        currency_format.set_num_format(preferred_currency.excel_format())

        percentage_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': 'white',
        })
        percentage_format.set_num_format('0%')

        bottom_percentage_format = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 10,
            'bg_color': 'white',
            'bottom': 1,
        })
        bottom_percentage_format.set_num_format('0%')

        worksheet = workbook.add_worksheet()

        stores = self.stores.all()
        data = ['Promedio', 'Mínimo', 'Moda']
        data_formula = [
            '=IFERROR(AVERAGE({0}:{1}), "")',
            '=IFERROR(MIN({0}:{1}), "")',
            '=IFERROR(MODE({0}:{1}), IFERROR(AVERAGE({0}:{1}), ""))'
        ]

        headers = []
        headers.extend([s.name for s in stores])
        headers.extend(data)
        headers.extend([self.brand_1.name, 'ATA', self.brand_2.name])
        headers.extend(data[::-1])
        headers.extend([s.name for s in stores[::-1]])
        headers.extend([""])
        headers.extend(data)

        for idx, header in enumerate(headers):
            worksheet.write(1, idx, header, header_format)

        row = 2
        brand_1_data_start = len(stores)
        segment_step = brand_1_data_start + len(data)
        brand_2_start = segment_step + 6
        brand_2_data_start = brand_2_start - 1
        stats_table_start = brand_2_start + len(stores) + 1

        avg_col_1 = brand_1_data_start
        min_col_1 = avg_col_1 + 1
        mode_col_1 = min_col_1 + 1

        avg_col_2 = brand_2_data_start
        min_col_2 = avg_col_2 - 1
        mode_col_2 = min_col_2 - 1

        worksheet.set_column(0, segment_step-1, 12)
        worksheet.set_column(brand_2_start, brand_2_start + segment_step-1, 12)
        worksheet.set_column(segment_step, segment_step, 25)
        worksheet.set_column(segment_step + 1, segment_step + 1, 20)
        worksheet.set_column(segment_step + 2, segment_step + 2, 25)

        for segment in self.segments.all():
            segment_rows = segment.rows.all()

            if len(segment_rows) == 1:
                worksheet.write(row, segment_step + 1,
                                segment.name, ata_format)
            else:
                worksheet.merge_range(
                    row, segment_step + 1,
                    row + len(segment_rows) - 1,
                    segment_step + 1,
                    segment.name,
                    ata_format)

            for idx, segment_row in enumerate(segment_rows):
                rows_count = len(segment_rows)

                currency_format_to_use = currency_format
                product_1_format_to_use = product_format
                product_2_format_to_use = product_format
                percentage_format_to_use = percentage_format

                is_bottom = rows_count - 1 == idx

                if is_bottom:
                    currency_format_to_use = bottom_currency_format
                    product_1_format_to_use = bottom_product_format
                    product_2_format_to_use = bottom_product_format
                    percentage_format_to_use = bottom_percentage_format

                if segment_row.is_product_1_highlighted:
                    product_1_format_to_use = product_1_highlight_format

                if segment_row.is_product_2_highlighted:
                    product_2_format_to_use = product_2_highlight_format

                col = 0
                for store in stores:
                    if segment_row.product_1:
                        entity1 = Entity.objects.filter(
                            store=store,
                            product=segment_row.product_1
                        ).order_by(
                            'active_registry__{}_price'.format(self.price_type)
                        ).select_related('currency', 'active_registry').first()

                        worksheet.write(row, segment_step,
                                        segment_row.product_1.name,
                                        product_1_format_to_use)

                        if entity1 and entity1.active_registry:
                            entity_currency = entity1.currency
                            price = getattr(entity1.active_registry, '{}_price'
                                            .format(self.price_type))
                            price = preferred_currency.convert_from(
                                price, entity_currency)
                            worksheet.write(
                                row, col, price, currency_format_to_use)
                        else:
                            worksheet.write(
                                row, col, "", currency_format_to_use)

                    else:
                        worksheet.write(
                            row, segment_step, "", product_1_format_to_use)
                        worksheet.write(row, col, "", currency_format_to_use)

                    if segment_row.product_2:
                        entity2 = Entity.objects.filter(
                            store=store,
                            product=segment_row.product_2
                        ).order_by(
                            'active_registry__{}_price'.format(self.price_type)
                        ).select_related('currency', 'active_registry').first()

                        worksheet.write(
                            row, segment_step + 2,
                            segment_row.product_2.name,
                            product_2_format_to_use)

                        if entity2 and entity2.active_registry:
                            entity_currency = entity2.currency
                            price = getattr(entity2.active_registry, '{}_price'
                                            .format(self.price_type))
                            price = preferred_currency.convert_from(
                                price, entity_currency)
                            worksheet.write(
                                row, brand_2_start + len(stores) - col - 1,
                                price, currency_format_to_use)
                        else:
                            worksheet.write(
                                row, brand_2_start + len(stores) - col - 1,
                                "", currency_format_to_use)
                    else:
                        worksheet.write(
                            row, segment_step + 2, "", product_2_format_to_use)
                        worksheet.write(
                            row, brand_2_start + len(stores) - col - 1, "",
                            currency_format_to_use)

                    col += 1

                for index, formula in enumerate(data_formula):
                    rowcol_1 = xl_rowcol_to_cell(row, brand_1_data_start+index)
                    formula_1 = formula.format(
                        xl_rowcol_to_cell(row, 0),
                        xl_rowcol_to_cell(row, len(stores)-1))

                    worksheet.conditional_format('{}:{}'.format(
                        xl_rowcol_to_cell(row, 0),
                        xl_rowcol_to_cell(row, len(stores) - 1),
                    ), {
                        'type': 'blanks',
                        'format': blanks_format
                    })

                    worksheet.conditional_format('{}:{}'.format(
                        xl_rowcol_to_cell(row, 0),
                        xl_rowcol_to_cell(row, len(stores) - 1),
                    ), {
                        'type': 'bottom',
                        'value': 1,
                        'format': highlight_format
                    })

                    rowcol_2 = xl_rowcol_to_cell(row, brand_2_data_start-index)
                    formula_2 = formula.format(
                        xl_rowcol_to_cell(row, brand_2_start),
                        xl_rowcol_to_cell(row, brand_2_start+len(stores)-1))

                    worksheet.conditional_format('{}:{}'.format(
                        xl_rowcol_to_cell(row, brand_2_start),
                        xl_rowcol_to_cell(row, brand_2_start + len(stores) - 1)
                    ), {
                        'type': 'blanks',
                        'format': blanks_format
                    })

                    worksheet.conditional_format('{}:{}'.format(
                        xl_rowcol_to_cell(row, brand_2_start),
                        xl_rowcol_to_cell(row, brand_2_start + len(stores) - 1)
                    ), {
                        'type': 'bottom',
                        'value': 1,
                        'format': highlight_format
                    })

                    worksheet.write_formula(rowcol_1, formula_1,
                                            currency_format_to_use)
                    worksheet.write_formula(rowcol_2, formula_2,
                                            currency_format_to_use)

                avg_rowcol = xl_rowcol_to_cell(row, stats_table_start)
                avg_formula = '=IF({0}=0, "", IFERROR({0}/{1}, ""))'.format(
                    xl_rowcol_to_cell(row, avg_col_1),
                    xl_rowcol_to_cell(row, avg_col_2)
                )
                worksheet.write_formula(
                    avg_rowcol, avg_formula, percentage_format_to_use)

                min_rowcol = xl_rowcol_to_cell(row, stats_table_start + 1)
                min_formula = '=IF({0}=0, "", IFERROR({0}/{1}, ""))'.format(
                    xl_rowcol_to_cell(row, min_col_1),
                    xl_rowcol_to_cell(row, min_col_2)
                )
                worksheet.write_formula(min_rowcol, min_formula,
                                        percentage_format_to_use)

                mode_rowcol = xl_rowcol_to_cell(row, stats_table_start+2)
                mode_formula = '=IF({0}=0, "", IFERROR({0}/{1}, ""))'.format(
                    xl_rowcol_to_cell(row, mode_col_1),
                    xl_rowcol_to_cell(row, mode_col_2)
                )
                worksheet.write_formula(
                    mode_rowcol, mode_formula, percentage_format_to_use)

                row += 1

        average_formula = '=AVERAGE({}: {})'

        avg_average_rowcol = xl_rowcol_to_cell(0, stats_table_start)
        avg_average_formula = average_formula.format(
            xl_rowcol_to_cell(2, stats_table_start),
            xl_rowcol_to_cell(row, stats_table_start))

        worksheet.write_formula(
            avg_average_rowcol, avg_average_formula, percentage_format)

        min_average_rowcol = xl_rowcol_to_cell(0, stats_table_start+1)
        min_average_formula = average_formula.format(
            xl_rowcol_to_cell(2, stats_table_start+1),
            xl_rowcol_to_cell(row, stats_table_start+1))

        worksheet.write_formula(
            min_average_rowcol, min_average_formula, percentage_format)

        mode_average_rowcol = xl_rowcol_to_cell(0, stats_table_start + 2)
        mode_average_formula = average_formula.format(
            xl_rowcol_to_cell(2, stats_table_start + 2),
            xl_rowcol_to_cell(row, stats_table_start + 2))

        worksheet.write_formula(
            mode_average_rowcol, mode_average_formula, percentage_format)

    def __str__(self):
        return '{} - {} - {} - {} - {}'.format(
            self.user, self.name, self.brand_1, self.brand_2, self.price_type)

    class Meta:
        app_label = 'brand_comparisons'
        ordering = ('user', 'name')
        permissions = (
            ['backend_list_brand_comparisons',
             'Can see brand comparisons in the backend'],
        )
