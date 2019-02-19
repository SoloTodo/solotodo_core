from celery import shared_task
from django.core.mail import EmailMessage
from django.http import QueryDict

from reports.forms.report_daily_prices_form import ReportDailyPricesForm
from reports.models import Report, ReportDownload
from solotodo.models import SoloTodoUser


@shared_task(queue='general', ignore_result=True, task_time_limit=1800)
def send_daily_prices_task(user_id, query_string):
    report = Report.objects.get(slug='daily_prices')
    user = SoloTodoUser.objects.get(id=user_id)

    q_dict = QueryDict(query_string)

    form = ReportDailyPricesForm(user, q_dict)
    assert form.is_valid()

    report_data = form.generate_report()

    report_filename = '{}.xlsx'.format(report_data['filename'])
    report_file = report_data['file']
    report_path = report_data['path']

    ReportDownload.objects.create(
        report=report,
        user=user,
        file=report_path
    )

    sender = SoloTodoUser().get_bot().email_recipient_text()
    message = 'Se adjunta el reporte de precios diarios para la categoría  ' \
              '"{}", con fechas entre {} y {}'\
        .format(form.cleaned_data['category'],
                form.cleaned_data['timestamp'].start.strftime('%Y-%m-%d'),
                form.cleaned_data['timestamp'].stop.strftime('%Y-%m-%d'))

    email = EmailMessage('Reporte precios diarios', message, sender,
                         [user.email])
    email.attach(
        report_filename, report_file,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    email.send()
