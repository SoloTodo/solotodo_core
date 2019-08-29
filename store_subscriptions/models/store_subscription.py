import io
import xlsxwriter

from django.db import models
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.utils import timezone

from solotodo.models import Store, Category, Entity, EntityHistory, \
    SoloTodoUser


class StoreSubscription(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    categories = models.ManyToManyField(Category)
    creation_date = models.DateTimeField(auto_now_add=True)

    def send_update(self):
        entities = Entity.objects.filter(
            store=self.store,
            category__in=self.categories.all())

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        worksheet = workbook.add_worksheet()

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10})

        headers = [
            'Producto',
            'Categoría',
            'SKU',
            'Precio Oferta Actual',
            'Precio Oferta Anterior',
            'Diferencia',
            'Precio Normal Actual',
            'Precio Normal Anterior',
            'Diferencia']

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1

        for entity in entities:
            product = entity.product
            category = entity.category
            active_registry = entity.active_registry
            compare_registry = self._get_comparison_registry(entity)

            if active_registry:
                current_offer_price = active_registry.offer_price
                current_normal_price = active_registry.normal_price

            if compare_registry:
                previous_offer_price = compare_registry.offer_price
                previous_normal_price = compare_registry.normal_price

            if current_normal_price == previous_normal_price and \
                    current_offer_price == previous_offer_price:
                continue

            col = 0
            worksheet.write(row, col, product.name)
            col += 1
            worksheet.write(row, col, category.name)
            col += 1
            worksheet.write(row, col, entity.sku)
            col += 1

            worksheet.write(row, col, current_offer_price)
            col += 1
            worksheet.write(row, col, previous_offer_price)
            col += 1

            if current_offer_price and previous_offer_price:
                worksheet.write(
                    row, col, current_offer_price-previous_offer_price)
                col += 1
            else:
                worksheet.write(row, col, 'N/A')
                col += 1

            worksheet.write(row, col, current_normal_price)
            col += 1
            worksheet.write(row, col, previous_normal_price)
            col += 1

            if current_normal_price and previous_normal_price:
                worksheet.write(
                    row, col, current_normal_price-previous_normal_price)
            else:
                worksheet.write(row, col, 'N/A')

            row += 1

        workbook.close()
        output.seek(0)

        file_value = output.getvalue()
        filename = 'store_changes_report.xlsx'

        sender = SoloTodoUser().get_bot().email_recipient_text()
        message = 'Probando'

        email = EmailMessage(
            'Reporte Tienda', message, sender, [self.user.email])

        email.attach(
            filename, file_value,
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet')
        email.send()

    @classmethod
    def _get_comparison_registry(cls, entity):
        search_date = timezone.now() - timezone.timedelta(days=1)
        ehs = EntityHistory.objects\
            .filter(entity=entity, timestamp__gte=search_date)\
            .order_by('timestamp')

        if ehs:
            return ehs[0]
        else:
            return None

    class Meta:
        app_label = 'store_subscriptions'
        ordering = ('-creation_date',)
