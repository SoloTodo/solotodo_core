from django.core.mail import EmailMessage
from django.core.management import BaseCommand
from django.utils import timezone

from brand_comparisons.models import BrandComparison
from solotodo.models import SoloTodoUser, Category


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--user_ids', nargs='+', type=int)
        parser.add_argument('--comparison_ids', nargs='+', type=int)
        parser.add_argument('--export_format', nargs='?', type=str,
                            default='xls')

    def handle(self, *args, **options):
        comparison_ids = options['comparison_ids']
        export_format = options['export_format']
        comparisons = BrandComparison.objects.filter(pk__in=comparison_ids)
        user_ids = options['user_ids']

        users = SoloTodoUser.objects.filter(pk__in=user_ids)
        emails = [user.email for user in users]

        sender = SoloTodoUser.get_bot().email_recipient_text()

        comparison_categories = Category.objects.filter(
            pk__in=comparisons.values('category_id'))

        message = """
        Buenos días,

        Se adjunta la Comparación de Precios ATA del día de hoy %d.%m.%Y
        para Chile en {}
        """.format(', '.join(str(x) for x in comparison_categories))
        message = timezone.now().strftime(message)

        subject = 'Comparación de modelos - %Y-%m-%d'
        subject = timezone.now().strftime(subject)

        email = EmailMessage(subject,
                             message, sender,
                             emails)

        for comparison_id in comparison_ids:
            comparison = BrandComparison.objects.get(pk=comparison_id)
            if export_format == 'xls_2':
                comparison_attachment = comparison.as_xls('2')['file']
            else:
                comparison_attachment = comparison.as_xls('1')['file']

            report_filename = '{}.xlsx'.format(comparison.name)

            email.attach(
                report_filename, comparison_attachment,
                'application/vnd.openxmlformats-'
                'officedocument.spreadsheetml.sheet')

        email.send()
