import io
import xlsxwriter

from django.db import models
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.utils import timezone

from .brand_comparison import BrandComparison
from solotodo.models import Store, Entity, EntityHistory, SoloTodoUser


class BrandComparisonAlert(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    brand_comparison = models.ForeignKey(
        BrandComparison, on_delete=models.CASCADE)
    stores = models.ManyToManyField(Store)
    last_check = models.DateTimeField()

    def check_for_changes(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)
        worksheet = workbook.add_worksheet()

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10})

        headers = [
            'Producto',
            'Tienda',
            'P. normal anterior',
            'P. normal nuevo',
            'P. oferta anterior',
            'P. oferta nuevo',
            'Producto comparado',
            'P. normal',
            'P. oferta']

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1

        for segment in self.brand_comparison.segments.all():
            for segment_row in segment.rows.all():
                for store in self.stores.all():
                    product_1 = segment_row.product_1
                    product_2 = segment_row.product_2
                    entity_1 = None
                    entity_2 = None

                    if product_1:
                        entities_1 = Entity.objects.filter(
                            store=store, product=product_1)\
                            .order_by('-id')

                        if entities_1:
                            entity_1 = entities_1[0]

                    if product_2:
                        entities_2 = Entity.objects.filter(
                            store=store, product=product_2) \
                            .order_by('-id')

                        if entities_2:
                            entity_2 = entities_2[0]

                    add_row = self.write_report_row(
                        worksheet, row, entity_1, entity_2, product_2)

                    if add_row:
                        row += 1

                    add_row = self.write_report_row(
                        worksheet, row, entity_2, entity_1, product_1)

                    if add_row:
                        row += 1

        workbook.close()
        output.seek(0)
        file_value = output.getvalue()

        if row > 1:
            sender = SoloTodoUser().get_bot().email_recipient_text()
            message = 'Probando'
            subject = 'Reporte comparacion de marcas'
            filename = 'Cambio comparacion de marcas.xlsx'

            email = EmailMessage(
                subject, message, sender, [self.user.email])

            email.attach(
                filename, file_value,
                'application/vnd.openxmlformats-officedocument.'
                'spreadsheetml.sheet')

            email.send()

    def write_report_row(
            self, worksheet, row, entity_1, entity_2, product_2):

        if not entity_1:
            return False

        date_from = self.last_check - timezone.timedelta(days=1)

        prev_registry = EntityHistory.objects.filter(
            entity=entity_1,
            timestamp__gte=date_from,
            timestamp__lte=self.last_check) \
            .order_by('-timestamp')

        if not prev_registry:
            prev_registry = None
        else:
            prev_registry = prev_registry[0]

        curr_registry = entity_1.active_registry

        if not prev_registry and not curr_registry:
            return False

        if not prev_registry or not curr_registry or \
                prev_registry.offer_price != \
                curr_registry.offer_price or \
                prev_registry.normal_price != \
                curr_registry.normal_price:

            col = 0
            worksheet.write(row, col, str(entity_1.product))
            col += 1
            worksheet.write(row, col, str(entity_1.store))
            col += 1

            if prev_registry:
                worksheet.write(
                    row, col, prev_registry.normal_price)
            else:
                worksheet.write(row, col, 'No disponible')
            col += 1

            if curr_registry:
                worksheet.write(
                    row, col, curr_registry.normal_price)
            else:
                worksheet.write(row, col, 'No disponible')
            col += 1

            if prev_registry:
                worksheet.write(
                    row, col, prev_registry.offer_price)
            else:
                worksheet.write(row, col, 'No disponible')
            col += 1

            if curr_registry:
                worksheet.write(
                    row, col, curr_registry.offer_price)
            else:
                worksheet.write(row, col, 'No disponible')
            col += 1

            if product_2:
                worksheet.write(
                    row, col, str(product_2))
                col += 1

            if entity_2 and entity_2.active_registry:
                comp_registry = entity_2.active_registry
                worksheet.write(
                    row, col, comp_registry.normal_price)
                col += 1
                worksheet.write(
                    row, col, comp_registry.offer_price)

            return True

        return False

    class Meta:
        app_label = 'brand_comparisons'
        ordering = ('user',)
