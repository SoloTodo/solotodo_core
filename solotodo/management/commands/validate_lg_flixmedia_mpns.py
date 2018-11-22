import re
import urllib

import requests
from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        with open('modelnames.txt') as f:
            for line in f.readlines():
                modelname = line.strip()
                url = 'http://media.flixcar.com/delivery/js/inpage/14021/cl/' \
                      'mpn/{}'.format(urllib.parse.quote(modelname))

                response = requests.get(url)
                product_match = re.search(r"product: '(\d+)'", response.text)
                product_id = int(product_match.groups()[0])

                if product_id:
                    print(modelname)
                else:
                    print('')
