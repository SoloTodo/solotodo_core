import requests
from bs4 import BeautifulSoup
from django.core.mail import EmailMessage
from django.core.management import BaseCommand

from solotodo.models import SoloTodoUser
from storescraper.stores import Falabella


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--emails', nargs='+')

    def handle(self, *args, **options):
        sender = SoloTodoUser().get_bot().email_recipient_text()

        try:
            data = self.obtain_data()
            available_entries = []
            for store, status in data.items():
                if status != 'Unavailable':
                    available_entries.append(store)

            if available_entries:
                message = 'Rodillo disponible en ' + str(available_entries)
                emails = options['emails']
                email = EmailMessage('Rodillo disponible!', message, sender,
                                     emails)
                email.send()
        except Exception:
            admin_user = SoloTodoUser.objects.get(pk=507)
            message = 'Error scrapeando rodillos'
            email = EmailMessage('Error scrapeando rodillos', message, sender,
                                 [admin_user.email])
            email.send()

    def obtain_data(self):
        session = requests.Session()
        data = {}

        # Sparta
        soup = BeautifulSoup(session.get(
            'https://sparta.cl/rodillo-tacx-flow-smart--'
            '37500000000t22400000.html').text, 'html.parser')
        if soup.find('div', 'available'):
            data['Sparta'] = 'Available'
        else:
            data['Sparta'] = 'Unavailable'

        # Garmin Store
        soup = BeautifulSoup(session.get(
            'https://www.garminstore.cl/flow-smart.html').text, 'html.parser')
        if soup.find('div', 'available'):
            data['Garmin Store'] = 'Available'
        else:
            data['Garmin Store'] = 'Unavailable'

        # Garmin Buy
        soup = BeautifulSoup(session.get(
            'https://buy.garmin.com/es-CL/CL/p/690890').text,
                             'html.parser')
        if soup.find('script', {'id': 'productSignup'}):
            data['Garmin Buy'] = 'Unavailable'
        else:
            data['Garmin Buy'] = 'Available'

        # Km 42
        soup = BeautifulSoup(session.get(
            'https://www.kilometro42.cl/rodillo-flow-smart-tacx').text,
                             'html.parser')
        if soup.find('meta', {'property': 'product:availability'})[
                'content'] == 'instock':
            data['Km 42'] = 'Available'
        else:
            data['Km 42'] = 'Unavailable'

        # Ebest
        soup = BeautifulSoup(session.get(
            'https://www.ebest.cl/rodillo-para-bicicleta-tacx-flow-smart.html'
            '').text, 'html.parser')
        if soup.find('p', 'out-of-stock'):
            data['Ebest'] = 'Unavailable'
        else:
            data['Ebest'] = 'Available'

        # Ruta del deporte
        session.headers['user-agent'] = 'curl/7.68.0'
        soup = BeautifulSoup(session.get(
            'https://www.rutadeporte.cl/rodillos-de-entrenamiento/'
            '4398-rodillo-de-entrenamiento-bicicleta-tacx-flow-smart-'
            '8714895058542.html').text, 'html.parser')
        if soup.find('span', 'product-unavailable'):
            data['Ruta del deporte'] = 'Unavailable'
        else:
            data['Ruta del deporte'] = 'Available'

        # Falabella
        url = 'https://www.falabella.com/falabella-cl/product/8698963/' \
              'Rodillo-Flow-Smart-Tacx/8698967'
        entry = Falabella.products_for_url(url, 'Roller')[0]
        if entry.is_available():
            data['Falabella'] = 'Available'
        else:
            data['Falabella'] = 'Unavailable'

        # BikeNew
        soup = BeautifulSoup(session.get(
            'https://bikenew.cl/producto/rodillo-flow-smart-tacx/').text,
                             'html.parser')
        if soup.find('p', 'out-of-stock'):
            data['BikeNew'] = 'Unavailable'
        else:
            data['BikeNew'] = 'Available'

        # GPS Aventura
        soup = BeautifulSoup(session.get(
            'https://www.gpsaventura.com/tacx-flow-smart').text,
                             'html.parser')
        if soup.find('meta', {'property': 'product:availability'})[
                'content'] == 'out of stock':
            data['GPS Aventura'] = 'Unavailable'
        else:
            data['GPS Aventura'] = 'Available'

        # Be Quick
        response = session.get(
            'https://www.bequick.cl/index.php?route=product/product&'
            'path=3_99341&product_id=1818')
        if response.status_code == 404:
            data['Be Quick'] = 'Unavailable'
        else:
            data['Be Quick'] = 'Available'

        return data
