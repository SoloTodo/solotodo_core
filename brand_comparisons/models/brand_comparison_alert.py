import io
import xlsxwriter

from django.db import models
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage

from .brand_comparison import BrandComparison
from solotodo.models import Store, Entity, EntityHistory, SoloTodoUser


class BrandComparisonAlert(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    brand_comparison = models.ForeignKey(
        BrandComparison, on_delete=models.CASCADE)
    stores = models.ManyToManyField(Store)
    last_check = models.DateTimeField()

    def check_for_changes(self):
        changed = False

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

                    entities_1 = Entity.objects.filter(
                        store=store, product=segment_row.product_1)\
                        .order_by('-id')

                    if entities_1:
                        entity_1 = entities_1[0]
                    else:
                        continue

                    prev_registry = EntityHistory.objects.filter(
                        entity=entity_1,
                        timestamp__lte=self.last_check)\
                        .order_by('-timestamp')[0]

                    curr_registry = entity_1.active_registry

                    if not prev_registry and not curr_registry:
                        continue

                    entities_2 = Entity.objects.filter(
                        store=store, product=segment_row.product_2)\
                        .order_by('-id')

                    if entities_2:
                        entity_2 = entities_2[0]
                    else:
                        entity_2 = None

                    if not prev_registry or not curr_registry or \
                            prev_registry.offer_price != \
                            curr_registry.offer_price or \
                            prev_registry.normal_price != \
                            curr_registry.normal_price:

                        changed = True
                        import ipdb
                        ipdb.set_trace()
                        col = 0
                        worksheet.write(row, col, str(entity_1.product))
                        col += 1
                        worksheet.write(row, col, str(store))
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

                        if segment_row.product_2:
                            worksheet.write(
                                row, col, str(segment_row.product_2))
                            col += 1

                        if entity_2 and entity_2.active_registry:
                            comp_registry = entity_2.active_registry
                            worksheet.write(
                                row, col, comp_registry.normal_price)
                            col += 1
                            worksheet.write(
                                row, col, comp_registry.offer_price)

                    row += 1

        workbook.close()
        output.seek(0)
        file_value = output.getvalue()

        if changed:
            print('Sending email')
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

    class Meta:
        app_label = 'brand_comparisons'
        ordering = ('user',)
