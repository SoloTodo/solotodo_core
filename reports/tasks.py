from celery import shared_task
from django.utils import timezone
from django.core.mail import EmailMessage
from django.http import QueryDict

from reports.forms.report_daily_prices_form import ReportDailyPricesForm
from reports.forms.report_current_prices_form import ReportCurrentPricesForm
from reports.models import Report, ReportDownload
from solotodo.models import SoloTodoUser, EsProduct


@shared_task(queue='general', ignore_result=True, task_time_limit=1800)
def send_current_prices_task(user_id, query_string):
    report = Report.objects.get(slug='current_prices')
    user = SoloTodoUser.objects.get(id=user_id)

    q_dict = QueryDict(query_string)

    form = ReportCurrentPricesForm(user, q_dict)
    assert form.is_valid()

    category = form.cleaned_data['category']
    spec_form_class = category.specs_form(form_type='es')
    spec_form = spec_form_class(q_dict)

    assert spec_form.is_valid()

    es_products_search = EsProduct.category_search(category)
    es_products_search = spec_form.get_es_products(es_products_search)
    report_data = form.generate_report(es_products_search)

    report_filename = '{}.xlsx'.format(report_data['filename'])
    report_file = report_data['file']
    report_path = report_data['path']

    print(report_filename)

    ReportDownload.objects.create(
        report=report,
        user=user,
        file=report_path)

    sender = SoloTodoUser().get_bot().email_recipient_text()
    message = 'Se adjunta el reporte de precios actuales para la categoría  ' \
              '"{}"'.format(form.cleaned_data['category'])

    subject = 'Reporte precios actuales {} - %Y-%m-%d'.format(category)
    subject = timezone.now().strftime(subject)

    email = EmailMessage(subject,
                         message, sender,
                         [user.email])
    email.attach(
        report_filename, report_file,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    email.send()


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
