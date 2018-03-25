import zipfile

import io

import pytz
from django.core.mail import EmailMessage
from django.core.management import BaseCommand
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user

from reports.forms.report_current_prices_form import ReportCurrentPricesForm
from reports.forms.report_weekly_prices_form import ReportWeeklyPricesForm
from solotodo.models import Category, Store, SoloTodoUser
from solotodo.utils import iso_to_gregorian


class Command(BaseCommand):
    def handle(self, *args, **options):
        user = SoloTodoUser.objects.get(pk=91552)

        conversion_dict = {
            8: 'DD',
            28: 'DDExt',
            29: 'FL',
            30: 'ME',
            39: 'SSD',
        }

        iso_year, iso_week, iso_day = timezone.now().isocalendar()

        start_date = pytz.UTC.localize(
            iso_to_gregorian(iso_year, iso_week - 1, 1))
        end_date = pytz.UTC.localize(
            iso_to_gregorian(iso_year, iso_week, 1))

        categories = Category.objects.filter(pk__in=conversion_dict.keys())
        stores = get_objects_for_user(user, 'view_store', Store)

        countries = set([store.country for store in stores])

        compressed_reports_io = io.BytesIO()
        compressed_attachments = zipfile.ZipFile(
            compressed_reports_io, mode='w', compression=zipfile.ZIP_DEFLATED)

        for country in countries:
            for category in categories:
                print('Making {} {}'.format(country, category))

                # Current prices

                form_data = {
                    'category': category.pk,
                    'countries': [country],
                }

                form = ReportCurrentPricesForm(user, form_data)
                assert form.is_valid()

                report_file = form.generate_report()['file']
                filename = 'RAvanzado_{}_{}.xlsx'.format(
                    country.iso_code,
                    conversion_dict[category.pk]
                )

                compressed_attachments.writestr(filename, report_file)

                # Week prices

                form_data = {
                    'timestamp_0': start_date,
                    'timestamp_1': end_date,
                    'category': category.pk,
                    'countries': [country],
                }

                form = ReportWeeklyPricesForm(user, form_data)
                assert form.is_valid()

                report_file = form.generate_report()['file']
                filename = 'TD_{}_{}.xlsx'.format(
                    country.iso_code,
                    conversion_dict[category.pk]
                )

                compressed_attachments.writestr(filename, report_file)

        compressed_attachments.close()
        compressed_reports_io.seek(0)
        filename = 'Reportes {}-{}.zip'.format(iso_year, iso_week - 1)
        attachment = (filename, compressed_reports_io.read(),
                      'application/zip')

        superusers = [u.email for u in SoloTodoUser.objects.filter(
            is_superuser=True)]

        email = EmailMessage(
            'Reportes Toshiba {}-{}'.format(iso_year, iso_week - 1),
            'Se adjuntan los reportes para Toshiba de la semana {} del año '
            '{}'.format(iso_week - 1, iso_year),
            'SoloBot <solobot@solotodo.com>',
            superusers + [user.email],
            attachments=[attachment]
        )

        email.send()
