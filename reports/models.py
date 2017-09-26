import io
import xlsxwriter
from django.core.files.base import ContentFile
from django.db import models

from solotodo.models import Entity
from solotodo_try.s3utils import PrivateS3Boto3Storage


class Report(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    def render_current_prices(self, user):
        es = Entity.objects.filter(product__isnull=False)\
            .get_available()\
            .filter_by_user_perms(user, 'view_entity')\
            .select_related()

        output = io.BytesIO()

        # Create a workbook and add a worksheet.
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()

        headers = [
            'Nombre',
            'Tienda',
            'Categoría',
            'SKU',
            'Precio normal',
            'Precio oferta',
            'Moneda',
            'URL',
            'Producto',
            'Fecha detección'
        ]

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header)

        for idx, e in enumerate(es):
            row = idx + 1
            worksheet.write(row, 0, e.name)
            worksheet.write(row, 1, str(e.store))
            worksheet.write(row, 2, str(e.category))
            worksheet.write(row, 3, e.sku)
            worksheet.write(row, 4, e.active_registry.normal_price)
            worksheet.write(row, 5, e.active_registry.offer_price)
            worksheet.write(row, 6, e.currency.iso_code)
            worksheet.write(row, 7, e.url)
            worksheet.write(row, 8, str(e.product))
            worksheet.write(row, 9, e.creation_date.date().strftime(
                '%Y-%m-%d'))

        workbook.close()

        output.seek(0)
        file_for_upload = ContentFile(output.getvalue())

        storage = PrivateS3Boto3Storage()
        path = storage.save('reports/{}.xlsx'.format(self.name),
                            file_for_upload)

        return storage.url(path)

    class Meta:
        ordering = ('name',)
        permissions = (
            ('view_report', 'Can view the report'),
        )
