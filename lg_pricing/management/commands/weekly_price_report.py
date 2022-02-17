import datetime
import io
import xlsxwriter

from django.utils import timezone
from django.core.management import BaseCommand
from django.core.mail import EmailMessage
from django.db.models import Min, DateField, F
from django.db.models.functions import Cast
from guardian.shortcuts import get_objects_for_group

from solotodo.models import Group
from solotodo.models import Category, Store, EntityHistory, SoloTodoUser


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--user_ids', nargs='+', type=int)
        parser.add_argument('--category_id', type=int)

    def handle(self, *args, **options):
        group = Group.objects.get(name="LG Chile")
        user_ids = options['user_ids']
        category_id = options['category_id']

        users = SoloTodoUser.objects.filter(pk__in=user_ids)
        emails = [user.email for user in users]

        new_condition = 'https://schema.org/NewCondition'
        category = Category.objects.get(id=category_id)
        stores = get_objects_for_group(group, 'view_store', Store)
        brands = [848, 996]

        # Determine date from/to

        now = timezone.now()
        date_to = (now - datetime.timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0)
        date_from = date_to - timezone.timedelta(days=7)

        # Query for entity histories
        ehs = EntityHistory.objects.filter(
            entity__category=category,
            entity__store__in=stores,
            entity__condition=new_condition,
            entity__product__brand__in=brands,
            entity__seller__isnull=True,
            timestamp__gte=date_from,
            timestamp__lt=date_to)\
            .get_available().annotate(date=Cast('timestamp', DateField()))

        # Group and Annotate
        ehs = ehs\
            .order_by('entity__product', 'entity__store', 'date')\
            .values('entity__product', 'entity__store', 'date')\
            .annotate(
                min_price=Min('offer_price'),
                product_name=F(
                    'entity__product__instance_model__unicode_representation'),
                store_name=F('entity__store__name'),
                brand=F('entity__product__brand__name'))

        # Generate Report
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        worksheet = workbook.add_worksheet()

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10
        })

        headers = [
            'Producto', 'Marca', 'Tienda', 'Fecha muestra', 'Precio mínimo']

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1

        for e in ehs:
            col = 0
            worksheet.write(row, col, e['product_name'])
            col += 1
            worksheet.write(row, col, e['brand'])
            col += 1
            worksheet.write(row, col, e['store_name'])
            col += 1
            worksheet.write(row, col, str(e['date']))
            col += 1
            worksheet.write(row, col, e['min_price'])

            row += 1

        workbook.close()
        output.seek(0)

        file_value = output.getvalue()

        sender = SoloTodoUser().get_bot().email_recipient_text()
        message = """
        Buenos días,

        Se adjunta el historico de precios para la semana %Y-%U.
        """
        message = date_from.strftime(message)

        subject = 'Reporte historico {} %Y-%W'.format(category)
        subject = date_from.strftime(subject)

        filename = 'weekly_price_report.xlsx'

        email = EmailMessage(subject, message, sender, emails)
        email.attach(
            filename,
            file_value,
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet')

        print(email.send())
