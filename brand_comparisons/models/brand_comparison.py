import io
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell

from django.db import models
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model

from solotodo.models import Brand, Store, Category, Entity
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

    def as_xls(self):
        preferred_currency = self.user.preferred_currency

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter'
        })

        currency_format = workbook.add_format()
        currency_format.set_font_size(10)
        currency_format.set_num_format(preferred_currency.excel_format())

        worksheet = workbook.add_worksheet()

        stores = self.stores.all()
        data = ['Promedio', 'Mínimo', 'Moda']
        data_formula = [
            '=IFERROR(AVERAGE({}:{}), "")',
            '=IFERROR(MIN({}:{}), "")',
            '=IFERROR(MODE({}:{}), "")'
        ]

        headers = []
        headers.extend([s.name for s in stores])
        headers.extend(data)
        headers.extend([self.brand_1.name, 'Segmentos', self.brand_2.name])
        headers.extend([s.name for s in stores])
        headers.extend(data)

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1
        brand_1_data_start = len(stores)
        segment_step = brand_1_data_start + len(data)
        brand_2_start = segment_step + 3
        brand_2_data_start = brand_2_start + len(stores)

        worksheet.set_column(0, segment_step-1, 12)
        worksheet.set_column(brand_2_start, brand_2_start + segment_step-1, 12)
        worksheet.set_column(segment_step, segment_step, 25)
        worksheet.set_column(segment_step + 1, segment_step + 1, 20)
        worksheet.set_column(segment_step + 2, segment_step + 2, 25)

        for segment in self.segments.all():
            segment_rows = segment.rows.all()

            if len(segment_rows) == 1:
                worksheet.write(row, segment_step + 1,
                                segment.name, header_format)
            else:
                worksheet.merge_range(
                    row, segment_step + 1,
                    row + len(segment_rows) - 1,
                    segment_step + 1,
                    segment.name,
                    header_format)

            for segment_row in segment_rows:
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
                                        header_format)

                        if entity1 and entity1.active_registry:
                            entity_currency = entity1.currency
                            price = getattr(entity1.active_registry, '{}_price'
                                            .format(self.price_type))
                            price = preferred_currency.convert_from(
                                price, entity_currency)
                            worksheet.write(row, col, price, currency_format)

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
                            header_format)

                        if entity2 and entity2.active_registry:
                            price = getattr(entity2.active_registry, '{}_price'
                                            .format(self.price_type))
                            worksheet.write(row, col + brand_2_start, price,
                                            currency_format)

                    col += 1

                for index, formula in enumerate(data_formula):
                    rowcol_1 = xl_rowcol_to_cell(row, brand_1_data_start+index)
                    formula_1 = formula.format(
                        xl_rowcol_to_cell(row, 0),
                        xl_rowcol_to_cell(row, len(stores)-1))

                    rowcol_2 = xl_rowcol_to_cell(row, brand_2_data_start+index)
                    formula_2 = formula.format(
                        xl_rowcol_to_cell(row, brand_2_start),
                        xl_rowcol_to_cell(row, brand_2_start + len(stores) - 1)
                    )

                    worksheet.write_formula(rowcol_1, formula_1,
                                            currency_format)
                    worksheet.write_formula(rowcol_2, formula_2,
                                            currency_format)

                row += 1

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
