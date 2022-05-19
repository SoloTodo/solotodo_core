from django.contrib.auth.models import Group
from django.core.mail import EmailMessage
from django.core.management import BaseCommand
from django.utils import timezone

from reports.forms.report_wtb_prices_form import ReportWtbPricesForm
from reports.forms.report_wtb_store_price_comparison_form import \
    ReportWtbStorePriceComparisonForm
from solotodo.models import SoloTodoUser


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--user_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        group = Group.objects.get(name='LG Chile')
        reference_user = SoloTodoUser.objects.filter(groups=group)[0]
        data = {
            'wtb_brand': 1,
            'store': 195,
            'competing_stores': [30, 9, 87, 5, 43, 11, 18, 67, 170, 12, 86],
        }
        form = ReportWtbStorePriceComparisonForm(reference_user, data)
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
