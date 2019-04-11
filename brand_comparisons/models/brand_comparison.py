import io
import xlsxwriter

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
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'center'
        })

        worksheet = workbook.add_worksheet()

        stores = self.stores.all()

        headers = []
        headers.extend([s.name for s in stores])
        headers.extend([self.brand_1.name, 'Segmentos', self.brand_2.name])
        headers.extend([s.name for s in stores])

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1
        segment_step = len(stores)
        brand_2_start = segment_step+3

        worksheet.set_column(0, segment_step-1, 15)
        worksheet.set_column(brand_2_start, brand_2_start + segment_step-1, 15)
        worksheet.set_column(segment_step, segment_step, 25)
        worksheet.set_column(segment_step + 1, segment_step + 1, 20)
        worksheet.set_column(segment_step + 2, segment_step + 2, 25)

        for segment in self.segments.all():
            for segment_row in segment.rows.all():
                col = 0
                for store in stores:
                    entity1 = Entity.objects\
                        .filter(store=store, product=segment_row.product_1)\
                        .first()
                    entity2 = Entity.objects\
                        .filter(store=store, product=segment_row.product_2)\
                        .first()

                    worksheet.write(row, segment_step,
                                    segment_row.product_1.name, header_format)
                    worksheet.write(row, segment_step + 2,
                                    segment_row.product_2.name, header_format)

                    if entity1 and entity1.active_registry:
                        price = getattr(entity1.active_registry, '{}_price'
                                        .format(self.price_type))
                        worksheet.write(row, col, price)

                    if entity2 and entity2.active_registry:
                        price = getattr(entity2.active_registry, '{}_price'
                                        .format(self.price_type))
                        worksheet.write(row, col + brand_2_start, price)

                    col += 1
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
