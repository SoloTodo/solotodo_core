from django.contrib.auth.models import Group
from django.core.mail import EmailMessage
from django.core.management import BaseCommand
from django.utils import timezone

from reports.forms.report_wtb_prices_form import ReportWtbPricesForm
from solotodo.models import SoloTodoUser


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--user_ids", nargs="+", type=int)
        parser.add_argument("--store_ids", nargs="+", type=int)
        parser.add_argument("--category_ids", nargs="*", type=int)

    def handle(self, *args, **options):
        group = Group.objects.get(name="LG Chile")
        reference_user = SoloTodoUser.objects.filter(groups=group)[0]
        data = {
            "wtb_brand": 1,
            "stores": options["store_ids"],
            "price_type": "offer_price",
        }
        category_ids = options["category_ids"]
        if category_ids:
            data["categories"] = category_ids
        form = ReportWtbPricesForm(reference_user, data)
        assert form.is_valid(), form.errors
        users = SoloTodoUser.objects.filter(pk__in=options["user_ids"])
        emails = [user.email for user in users]
        sender = SoloTodoUser.get_bot().email_recipient_text()

        message = """
        Buenos días,

        Se adjunta la Comparación de Precios WTB del día de hoy %d.%m.%Y
        """
        message = timezone.now().strftime(message)

        subject = "Comparación de precios WTB - %Y-%m-%d"
        subject = timezone.now().strftime(subject)

        email = EmailMessage(subject, message, sender, emails)

        report_file = form.generate_report()["file"]

        email.attach(
            "wtb_price_comparison_report.xlsx",
            report_file,
            "application/vnd.openxmlformats-" "officedocument.spreadsheetml.sheet",
        )

        email.send()
