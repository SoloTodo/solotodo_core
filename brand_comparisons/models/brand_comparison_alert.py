import io
import xlsxwriter

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.conf import settings

from .brand_comparison import BrandComparison
from solotodo.models import Store, Entity, EntityHistory, SoloTodoUser


class BrandComparisonAlert(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    brand_comparison = models.ForeignKey(
        BrandComparison, on_delete=models.CASCADE)
    stores = models.ManyToManyField(Store)
    last_check = models.DateTimeField(auto_now_add=True)

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
            'Marca',
            'Tienda',
            'P. normal',
            'Variación',
            'P. oferta',
            'Variación',
            '-',
            'Producto comparado',
            'P. normal',
            'Diferencia',
            'P. oferta',
            'Diferencia']

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
                            store=store, product=product_1,
                            active_registry__cell_monthly_payment__isnull=True
                        ).order_by('-id')

                        if entities_1:
                            entity_1 = entities_1[0]

                    if product_2:
                        entities_2 = Entity.objects.filter(
                            store=store, product=product_2,
                            active_registry__cell_monthly_payment__isnull=True
                        ).order_by('-id')

                        if entities_2:
                            entity_2 = entities_2[0]

                    add_row = self.write_report_row(
                        workbook, worksheet, row,
                        entity_1, entity_2, product_2)

                    if add_row:
                        row += 1

        for segment in self.brand_comparison.segments.all():
            for segment_row in segment.rows.all():
                for store in self.stores.all():
                    product_1 = segment_row.product_1
                    product_2 = segment_row.product_2
                    entity_1 = None
                    entity_2 = None

                    if product_1:
                        entities_1 = Entity.objects.filter(
                            store=store, product=product_1,
                            active_registry__cell_monthly_payment__isnull=True
                        ).order_by('-id')

                        if entities_1:
                            entity_1 = entities_1[0]

                    if product_2:
                        entities_2 = Entity.objects.filter(
                            store=store, product=product_2,
                            active_registry__cell_monthly_payment__isnull=True
                        ).order_by('-id')

                        if entities_2:
                            entity_2 = entities_2[0]

                    add_row = self.write_report_row(
                        workbook, worksheet, row,
                        entity_2, entity_1, product_1)

                    if add_row:
                        row += 1

        worksheet.autofilter(0, 0, row - 1, len(headers) - 1)

        workbook.close()
        output.seek(0)
        file_value = output.getvalue()

        if row > 1:
            sender = SoloTodoUser().get_bot().email_recipient_text()
            date = timezone.now().strftime('%Y-%m-%d')
            stores = ", ".join([s.name for s in self.stores.all()])

            message = 'Se adjuntan los cambios de la comparativa {} para el ' \
                'día {} de las tiendas {}'.format(
                    self.brand_comparison.name, date, stores)

            html_message = render_to_string(
                'brand_comparison_alert_mail.html',
                {
                    'summary': mark_safe(message),
                    'brand_comparison': self.brand_comparison,
                    'solotodo_com_domain': Site.objects.get(
                        pk=settings.SOLOTODO_PRICING_SITE_ID).domain
                })

            subject = 'Reporte comparativa {} - {}'.format(
                self.brand_comparison.name, date)
            filename = '{}-{}.xlsx'.format(self.brand_comparison.name, date)

            email = EmailMultiAlternatives(
                subject, message, sender, [self.user.email])
            email.attach_alternative(html_message, 'text/html')

            email.attach(
                filename, file_value,
                'application/vnd.openxmlformats-officedocument.'
                'spreadsheetml.sheet')

            email.send()

        self.last_check = timezone.now()
        self.save()

    def write_report_row(
            self, workbook, worksheet, row, entity_1, entity_2, product_2):

        if not entity_1:
            return False

        currency_format_red = workbook.add_format()
        currency_format_red.set_font_size(10)
        currency_format_red.set_num_format(entity_1.currency.excel_format())
        currency_format_red.set_font_color('red')

        currency_format_green = workbook.add_format()
        currency_format_green.set_font_size(10)
        currency_format_green.set_num_format(entity_1.currency.excel_format())
        currency_format_green.set_font_color('green')

        currency_format_black = workbook.add_format()
        currency_format_black.set_font_size(10)
        currency_format_black.set_num_format(entity_1.currency.excel_format())
        currency_format_black.set_font_color('black')

        right_align_format = workbook.add_format()
        right_align_format.set_font_size(10)
        right_align_format.set_align('right')

        date_from = self.last_check - timezone.timedelta(days=1)

        prev_registry = EntityHistory.objects.filter(
            entity=entity_1,
            timestamp__gte=date_from,
            timestamp__lte=self.last_check,
            cell_monthly_payment__isnull=True
        ).order_by('-timestamp')

        if not prev_registry:
            prev_registry = None
        else:
            prev_registry = prev_registry[0]

        curr_registry = entity_1.active_registry

        if not prev_registry and not curr_registry:
            return False

        if prev_registry and curr_registry and \
                prev_registry.offer_price == curr_registry.offer_price and\
                prev_registry.normal_price == curr_registry.normal_price:
            return False

        col = 0
        worksheet.write(row, col, str(entity_1.product))
        col += 1
        worksheet.write(row, col, str(entity_1.product.brand))
        col += 1
        worksheet.write(row, col, str(entity_1.store))

        col += 1

        curr_normal_price = None
        curr_offer_price = None
        prev_normal_price = None
        prev_offer_price = None

        if curr_registry:
            curr_normal_price = curr_registry.normal_price
            curr_offer_price = curr_registry.offer_price

        if prev_registry:
            prev_normal_price = prev_registry.normal_price
            prev_offer_price = prev_registry.offer_price

        if curr_normal_price:
            worksheet.write(row, col, curr_normal_price, currency_format_black)
        else:
            worksheet.write(row, col, 'No disponible', right_align_format)
        col += 1

        if curr_normal_price and prev_normal_price:
            difference = curr_normal_price-prev_normal_price
            if difference < 0:
                currency_format = currency_format_green
            elif difference > 0:
                currency_format = currency_format_red
            else:
                currency_format = None
                difference = ""

            worksheet.write(row, col, difference, currency_format)
        elif curr_normal_price:
            worksheet.write(row, col, 'Nuevo', right_align_format)
        elif prev_normal_price:
            worksheet.write(row, col, 'Agotado', right_align_format)
        else:
            worksheet.write(row, col, '')
        col += 1

        if curr_offer_price:
            worksheet.write(row, col, curr_offer_price, currency_format_black)
        else:
            worksheet.write(row, col, 'No disponible', right_align_format)
        col += 1

        if curr_offer_price and prev_offer_price:
            difference = curr_offer_price-prev_offer_price
            if difference < 0:
                currency_format = currency_format_green
            elif difference > 0:
                currency_format = currency_format_red
            else:
                currency_format = None
                difference = ""

            worksheet.write(row, col, difference, currency_format)
        elif curr_offer_price:
            worksheet.write(row, col, 'Nuevo', right_align_format)
        elif prev_offer_price:
            worksheet.write(row, col, 'Agotado', right_align_format)
        else:
            worksheet.write(row, col, '')
        col += 2

        if product_2:
            worksheet.write(row, col, str(product_2))
            col += 1

        if entity_2 and entity_2.active_registry:
            comp_registry = entity_2.active_registry
            comp_normal_price = comp_registry.normal_price
            comp_offer_price = comp_registry.normal_price

            worksheet.write(row, col, comp_normal_price, currency_format_black)
            col += 1

            if curr_normal_price:
                difference = comp_normal_price - curr_normal_price
                if difference < 0:
                    currency_format = currency_format_green
                elif difference > 0:
                    currency_format = currency_format_red
                else:
                    currency_format = None
                    difference = ""

                worksheet.write(row, col, difference, currency_format)
            else:
                worksheet.write(row, col, '')
            col += 1

            worksheet.write(row, col, comp_offer_price, currency_format_black)
            col += 1

            if curr_offer_price:
                difference = comp_offer_price - curr_offer_price
                if difference < 0:
                    currency_format = currency_format_green
                elif difference > 0:
                    currency_format = currency_format_red
                else:
                    currency_format = None
                    difference = ""

                worksheet.write(row, col, difference, currency_format)
            else:
                worksheet.write(row, col, '')
            col += 1

        elif product_2:
            worksheet.write(row, col, 'No disponible', right_align_format)
            col += 1
            worksheet.write(row, col, '')
            col += 1
            worksheet.write(row, col, 'No disponible', right_align_format)
            col += 1
            worksheet.write(row, col, '')

        return True

    class Meta:
        app_label = 'brand_comparisons'
        ordering = ('user',)
