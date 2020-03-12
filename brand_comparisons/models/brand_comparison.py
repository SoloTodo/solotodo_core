import io
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell

from django.db import models
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model

from solotodo.models import Brand, Store, Category, Entity, Product
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

    def as_xls(self):
        preferred_currency = self.user.preferred_currency

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
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
                product_format_to_use = product_format
                percentage_format_to_use = percentage_format
                if rows_count - 1 == idx:
                    currency_format_to_use = bottom_currency_format
                    product_format_to_use = bottom_product_format
                    percentage_format_to_use = bottom_percentage_format

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
                                        product_format_to_use)

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
                            row, segment_step, "", product_format_to_use)
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
                            product_format_to_use)

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
                            row, segment_step + 2, "", product_format_to_use)
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
