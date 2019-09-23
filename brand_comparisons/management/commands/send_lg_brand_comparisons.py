from django.core.mail import EmailMessage
from django.core.management import BaseCommand
from django.utils import timezone

from brand_comparisons.models import BrandComparison
from solotodo.models import SoloTodoUser


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--user_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        comparison_ids = [4, 6]
        user_ids = options['user_ids']

        users = SoloTodoUser.objects.filter(pk__in=user_ids)
        emails = [user.email for user in users]

        sender = SoloTodoUser.get_bot().email_recipient_text()
        message = """
        Buenas tardes,

        Se adjuntan las comparaciones de modelos para el día %Y-%m-%d
        """
        message = timezone.now().strftime(message)

        subject = 'Comparación de modelos - %Y-%m-%d'
        subject = timezone.now().strftime(subject)

        email = EmailMessage(subject,
                             message, sender,
                             emails)

        for comparison_id in comparison_ids:
            comparison = BrandComparison.objects.get(pk=comparison_id)
            comparison_attachment = comparison.as_xls()['file']

            report_filename = '{}.xlsx'.format(comparison.name)

            email.attach(
                report_filename, comparison_attachment,
                'application/vnd.openxmlformats-'
                'officedocument.spreadsheetml.sheet')

        email.send()
