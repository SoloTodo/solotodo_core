import csv
import requests
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from django.http import HttpResponse
from django.conf import settings

from wtb.models import WtbBrand
from solotodo.models import Entity

import json


class LgWtbViewSet(ViewSet):
    @action(detail=False, methods=['get'])
    def fb_feed(self, request):
        brand = WtbBrand.objects.get(pk=1)
        store_ids = [9, 18, 11, 30, 60, 5, 43]

        category_taxonomy_mapping = {
            36: ('Electronics > Electronics Accessories',
                 'electronics > portable audio & video'),
            37: ('Electronics > Computers > Desktop Computers',
                 'electronics > computers & tablets > desktop computers '),
            50: ('Electronics > Audio > Audio Components > '
                 'Headphones & Headsets',
                 'electronics > portable audio & video'),
            51: ('Electronics', 'electronics'),
            6: ('Electronics > Communications > Telephony > Mobile Phones',
                'electronics > cell phones & smart watches > cell phones'),
            28: ('Electronics > Electronics Accessories > '
                 'Computer Components > Storage Devices > Hard Drives',
                 'electronics > computers & tablets > '
                 'computer components & hardware'),
            25: ('Electronics > Audio > Audio Players & Recorders',
                 'electronics > home audio & video'),
            29: ('Electronics > Electronics Accessories > '
                 'Computer Components > Storage Devices > USB Flash Drives',
                 'electronics > accessories > computer peripherals'),
            17: ('Home & Garden > Kitchen & Dining > Kitchen Appliances > '
                 'Microwave Ovens',
                 'home > large appliances > microwave ovens'),
            16: ('Electronics > Print, Copy, Scan & Fax > '
                 'Printers, Copiers & Fax Machines',
                 'electronics > printers & scanners'),
            19: ('Home & Garden > Household Appliances > '
                 'Laundry Appliances > Washing Machines',
                 'home > large appliances > washers & dryers'),
            4: ('Electronics > Video > Computer Monitors',
                'electronics > tvs & monitors > computer monitors'),
            40: ('Electronics > Electronics Accessories > '
                 'Computer Components > Input Devices > Mice & Trackballs',
                 'electronics > accessories > computer peripherals'),
            1: ('Electronics > Computers > Laptops',
                'electronics > computers & tablets > laptops'),
            31: ('Electronics > Video > Projectors',
                 'electronics > projectors'),
            15: ('Home & Garden > Kitchen & Dining > Kitchen Appliances > '
                 'Refrigerators',
                 'home > large appliances > refrigerators & freezers'),
            26: ('Electronics > Video > Video Players & Recorders > '
                 'DVD & Blu-ray Players',
                 'electronics > home audio & video'),
            11: ('Electronics > Video > Televisions',
                 'electronics > tvs & monitors > tvs'),
            46: ('Electronics > Electronics Accessories > '
                 'Computer Components > Storage Devices > Optical Drives',
                 'electronics > accessories > computer peripherals'),
            48: ('Apparel & Accessories > Jewelry > Watches',
                 'electronics > cell phones & smart watches > '
                 'cell phone & smart watch accessories')
        }

        response = HttpResponse(
            content_type='text/csv'
        )
        response['Content-Disposition'] = \
            'attachment; filename="feed.csv"'
        writer = csv.writer(response, quoting=csv.QUOTE_NONNUMERIC)

        titles = [
            'id',
            'title',
            'description',
            'availability',
            'inventory',
            'condition',
            'price',
            'link',
            'image_link',
            'brand',
            'google_product_category',
            'fb_product_category',
            'product_type'
        ]
        writer.writerow(titles)

        wtb_entities = brand.wtbentity_set.filter(
            is_active=True, product__isnull=False)

        for wtb_entity in wtb_entities:
            product = wtb_entity.product
            entities = Entity.objects.filter(
                product=product,
                store__in=store_ids,
                seller__isnull=True) \
                .get_available() \
                .order_by('active_registry__offer_price')
            if not entities:
                continue
            entity = entities[0]

            wtb_entity_name_parts = wtb_entity.name.split(' - ')
            if len(wtb_entity_name_parts) == 2:
                title, description = wtb_entity_name_parts
            else:
                # A cell phone with color variants
                title = wtb_entity.name.split(' (')[0]
                description = wtb_entity.name

            price = '{} CLP'.format(entity.active_registry.offer_price)

            google_taxonomy, fb_taxonomy = \
                category_taxonomy_mapping[wtb_entity.category_id]

            row = [
                wtb_entity.key,
                title,
                description,
                'in stock',
                1,
                'new',
                price,
                wtb_entity.url,
                wtb_entity.picture_url,
                'LG',
                google_taxonomy,
                fb_taxonomy,
                wtb_entity.section
            ]
            writer.writerow(row)

        return response

class SendinblueViewSet(ViewSet):
    @action(detail=False, methods=['post'])
    def contacts(self, request):
        url = "https://api.sendinblue.com/v3/contacts"
        payload = request.data
        headers = {
            'accept': "application/json",
            'content-type': "application/json",
            'api-key': settings.SENDINBLUE_KEY
        }

        response = requests.request(
            "POST", url, data=json.dumps(payload), headers=headers)

        response_headers = {
            'content-type': 'application/json'
        }

        if response.text:
            data = json.loads(response.text)
        else:
            data = None

        return Response(
            data=data,
            status=response.status_code,
            headers=response_headers)
