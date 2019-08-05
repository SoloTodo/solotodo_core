from django.db import models
from django.utils import timezone
from solotodo.models import Lead
from solotodo_core.settings import local

import requests
import pytz
from decimal import Decimal
from datetime import date, datetime
from bs4 import BeautifulSoup


class SoicosConversion(models.Model):
    STATUS_CHOICES = (
        (1, 'OK'),
        (2, 'Canceled'),
        (3, 'Pending'),
        (4, 'Blocked'),
        (5, 'Invalid country'))

    lead = models.OneToOneField(Lead, on_delete=models.CASCADE)
    creation_date = models.DateTimeField()
    validation_date = models.DateTimeField(blank=True, null=True)
    ip = models.GenericIPAddressField()
    transaction_id = models.CharField(max_length=256)
    payout = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.IntegerField(choices=STATUS_CHOICES)

    def __str__(self):
        return '{} - {}'.format(self.lead, self.creation_date)

    @classmethod
    def update_from_soicos(cls):
        soicos_url = "https://soicos.com"
        session = requests.Session()
        response = session.get(soicos_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        token = soup.find('input', {'name': '_token'})['value']

        post_data = {
            '_token': token,
            'email': local.SOICOS_USER,
            'password': local.SOICOS_PASS,
        }

        response = session.post(soicos_url + "/login", data=post_data)

        today_date = date.today().strftime("%Y-%m-%d")
        page = 1

        while True:
            conversions_url = "/publisher/reports/conversions?" \
                              "date_based=date_created&" \
                              "status=All&" \
                              "ds_date_from=2019-01-01&" \
                              "ds_date_to={}&" \
                              "page={}".format(today_date, page)

            response = session.get(soicos_url + conversions_url)

            soup = BeautifulSoup(response.text, 'html.parser')

            table = soup.find('table', {'id': 'conversions_table'})
            rows = table.find('tbody').findAll('tr')

            if not rows:
                break

            for row in rows:
                contents = row.findAll('td')
                uuid_container = contents[6].text

                if not uuid_container or len(uuid_container.split('_')) < 3:
                    continue

                uuid = uuid_container.split('_')[-1]

                try:
                    lead = Lead.objects.get(uuid=uuid)
                except Lead.DoesNotExist:
                    continue

                creation_date = datetime.strptime(
                    contents[2].text, '%d/%m/%Y %H:%M:%S')

                creation_date = pytz.timezone(
                    "Chile/Continental").localize(creation_date)

                if contents[3].text != '-':
                    validation_date = datetime.strptime(
                        contents[3].text, '%d/%m/%Y')
                    validation_date = pytz.timezone(
                        "Chile/Continental").localize(validation_date)
                else:
                    validation_date = None

                ip = contents[4].text
                transaction_id = contents[7].text
                payout = Decimal(
                    contents[8].text.replace(',', '.'))
                transaction_total = Decimal(
                    contents[9].text.replace('.', '').replace(',', '.'))

                status = 0

                for choice in cls.STATUS_CHOICES:
                    if choice[1] == contents[10].text:
                        status = choice[0]
                        break

                try:
                    conversion = SoicosConversion.objects.get(lead__uuid=uuid)
                    conversion.validation_date = validation_date
                    conversion.status = status
                except SoicosConversion.DoesNotExist:
                    conversion = SoicosConversion(
                        lead=lead,
                        creation_date=creation_date,
                        validation_date=validation_date,
                        ip=ip,
                        transaction_id=transaction_id,
                        payout=payout,
                        transaction_total=transaction_total,
                        status=status)

                conversion.save()

            page += 1

            # download_url =
            # 'https://solotodo-core.s3.amazonaws.com/report.csv'
            # response = session.get(download_url)
            #
            # f = StringIO(response.text)
            # reader = csv.reader(f, delimiter=',')
            #
            # first_row = True
            #
            # for row in reader:
            #     if first_row:
            #         first_row = False
            #         continue
            #
            #     uuid_container = row[12]
            #
            #     if uuid_container ==
            #     '-' or len(uuid_container.split('_')) < 3:
            #         continue
            #
            #     uuid = uuid_container.split('_')[-1]
            #
            #     print(uuid)
            #
            #     try:
            #         lead = Lead.objects.get(uuid=uuid)
            #     except Lead.DoesNotExist:
            #         continue
            #
            #     creation_date = datetime.strptime(
            #         row[8], '%Y-%m-%d %H:%M:%S')
            #
            #     creation_date = pytz.timezone(
            #         "Chile/Continental").localize(creation_date)
            #
            #     validation_date = datetime.strptime(
            #         row[8], '%Y-%m-%d %H:%M:%S')
            #
            #     validation_date = pytz.timezone(
            #         "Chile/Continental").localize(validation_date)

    class Meta:
        app_label = 'soicos_conversions'
