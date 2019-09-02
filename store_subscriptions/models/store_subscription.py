import io
import xlsxwriter

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.utils import timezone
from django.conf import settings

from solotodo.models import Store, Category, Entity, EntityHistory, \
    SoloTodoUser


class StoreSubscription(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    categories = models.ManyToManyField(Category)
    creation_date = models.DateTimeField(auto_now_add=True)

    def send_update(self):
        entities = Entity.objects.filter(
            product__isnull=False,
            store=self.store,
            category__in=self.categories.all()
        ).select_related(
            'product__brand', 'category', 'active_registry'
        )

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
            'Marca',
            'SKU',
            'Precio Oferta Anterior',
            'Precio Oferta Actual',
            'Diferencia Precio Oferta',
            'Precio Normal Anterior',
            'Precio Normal Actual',
            'Diferencia Precio Normal']

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1

        for entity in entities:
            product = entity.product
            category = entity.category
            active_registry = entity.active_registry
            compare_registry = self._get_comparison_registry(entity)

            current_offer_price = None
            current_normal_price = None
            previous_offer_price = None
            previous_normal_price = None

            if active_registry and active_registry.stock != 0:
                current_offer_price = active_registry.offer_price
                current_normal_price = active_registry.normal_price

            if compare_registry and compare_registry.stock != 0:
                previous_offer_price = compare_registry.offer_price
                previous_normal_price = compare_registry.normal_price

            if current_normal_price == previous_normal_price and \
                    current_offer_price == previous_offer_price:
                continue

            domain = Site.objects.get(
                pk=settings.SOLOTODO_PRICING_SITE_ID).domain

            url = 'https://{}/skus/{}'.format(domain, entity.id)

            col = 0
            worksheet.write(row, col, str(product))
            col += 1
            worksheet.write(row, col, str(category))
            col += 1
            worksheet.write(row, col, str(product.brand))
            col += 1
            worksheet.write_url(row, col, url, string=entity.sku)
            col += 1

            worksheet.write(row, col, previous_offer_price or 'No Disponible')
            col += 1
            worksheet.write(row, col, current_offer_price or 'No Disponible')
            col += 1

            if current_offer_price and previous_offer_price:
                worksheet.write(
                    row, col, current_offer_price-previous_offer_price)
            else:
                worksheet.write(row, col, 'N/A')

            col += 1
            worksheet.write(row, col, previous_normal_price or 'No Disponible')
            col += 1
            worksheet.write(row, col, current_normal_price or 'No Disponible')
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
        search_date_to = timezone.now() - timezone.timedelta(days=1)
        search_date_from = timezone.now() - timezone.timedelta(days=2)
        ehs = EntityHistory.objects \
            .filter(
                entity=entity,
                timestamp__gte=search_date_from,
                timestamp__lte=search_date_to) \
            .order_by('-timestamp')

        if ehs:
            return ehs[0]
        else:
            return None

    class Meta:
        app_label = 'store_subscriptions'
        ordering = ('-creation_date',)
        permissions = (
            ['backend_list_store_subscriptions',
             'Can see store subscription list in the backend'],
        )
