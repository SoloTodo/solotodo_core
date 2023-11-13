import requests
from django.conf import settings
from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        session = requests.Session()
        session.headers['Authorization'] = 'Bearer {}'.format(
            settings.DUEMINT_KEY)
        endpoint = 'https://api.duemint.com/v1/getDocuments?status=3&expandClient=1&expandContact=1'
        response = session.get(endpoint).json()

        for item in response['items']:
            for contact in item['client']['contacts']:
                print(contact['email'], item['client']['url'], sep='\t')