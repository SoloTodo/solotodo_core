from django.contrib.auth.models import Group
from django.core.mail import EmailMessage
from django.core.management import BaseCommand
from django.utils import timezone
from guardian.shortcuts import get_objects_for_group

from reports.forms.report_wtb_prices_form import ReportWtbPricesForm
from solotodo.models import SoloTodoUser, Store


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--user_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        group = Group.objects.get(name='LG Chile')
        reference_user = SoloTodoUser.objects.filter(groups=group)[0]

        all_stores = get_objects_for_group(group, 'view_store', Store)
        store_ids = [30, 9, 87, 5, 43, 195, 11, 18, 67, 170, 12, 86]
        secondary_store_ids = [x.id for x in all_stores if x.id not in store_ids]

        data = {
            'wtb_brand': 1,
            'stores': store_ids,
            'secondary_stores': secondary_store_ids,
            'price_type': 'offer_price'
        }
        form = ReportWtbPricesForm(reference_user, data)
        assert form.is_valid(), form.errors

        user_ids = options['user_ids']

        users = SoloTodoUser.objects.filter(pk__in=user_ids)
        emails = [user.email for user in users]
        sender = SoloTodoUser.get_bot().email_recipient_text()

        message = """
        Buenos días,

        Se adjunta la Comparación de Precios WTB del día de hoy %d.%m.%Y
        """
        message = timezone.now().strftime(message)

        subject = 'Comparación de precios WTB - %Y-%m-%d'
        subject = timezone.now().strftime(subject)

        email = EmailMessage(subject,
                             message, sender,
                             emails)

        report_file = form.generate_report()['file']

        email.attach(
            'wtb_price_comparison_report.xlsx', report_file,
            'application/vnd.openxmlformats-'
            'officedocument.spreadsheetml.sheet')

        email.send()
