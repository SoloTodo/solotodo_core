import io
import csv
import requests
from collections import OrderedDict

from django.db.models import Min
from django.utils import timezone
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError
from django.http import HttpResponse
from django.conf import settings

from wtb.models import WtbEntity, WtbBrand
from solotodo.models import Entity, Product
from solotodo.utils import format_currency
from solotodo.serializers import ProductAvailableEntitiesMinimalSerializer

import json


class LgWtbViewSet(ViewSet):
    @action(detail=False, methods=['get'])
    def entity_data(self, request):
        params = request.GET
        product = params.get('product')
        model_id = params.get('model_id')
        sub_model_id = params.get('sub_model_id')
        data_type = params.get('type')
        callback = params.get('callback')

        if not product and not model_id and not sub_model_id:
            return Response(
                {'detail': 'product, model_id or sub_model_id must be given'},
                status=400
            )

        wtb_entities = WtbEntity.objects.filter(brand=1)

        if sub_model_id:
            wtb_entities = wtb_entities.filter(key=sub_model_id)
        elif model_id:
            wtb_entities = wtb_entities.filter(key=model_id)
        else:
            wtb_entities = wtb_entities.filter(name__contains=product)

        products = [w.product for w in wtb_entities]

        store_ids = [30, 61, 60, 97, 38, 9, 87, 5, 43, 23, 37, 11, 12, 18, 67,
                     167, 85, 181, 195, 197, 224]

        entities = Entity.objects \
            .filter(product__in=products, store__in=store_ids) \
            .get_available().order_by('active_registry__offer_price') \
            .select_related('product', 'store')

        retailers = []
        store_names = []

        for entity in entities:
            if entity.store.name in store_names:
                continue
            price = entity.active_registry.offer_price
            formatted_price = format_currency(price, places=0)
            store_names.append(entity.store.name)
            product_images = entity.picture_urls_as_list()
            url = entity.affiliate_url('LWTB_')
            retailer = {
                "display_name": entity.store.name,
                "instock": True,
                "logo_url": entity.store.logo.url,
                "deeplink_url": url or entity.url,
                "price": str(price),
                "priceformatted": formatted_price,
                "currency_code": "CLP",
                "currency_symbol": "$",
                "sku": entity.sku,
                "product_images": product_images
            }

            retailers.append(retailer)

        response = {
            "available_option_groups": None,
            "isRandomOrder": False,
            "itrack": "",
            "lang": "es-CL",
            "products": [
                {
                    "country_code": "CHL",
                    "retailers": retailers
                }
            ]
        }

        if data_type == 'jsonp':
            if not callback:
                raise ParseError('Missing callback')
            return HttpResponse(callback+'('+json.dumps(response)+')',
                                content_type='text/javascript')

        return Response(response)

    @action(detail=False, methods=['get'])
    def exponea_catalog(self, request):
        brand = WtbBrand.objects.get(pk=1)
        wtb_entities = brand.wtbentity_set.filter(
            product__isnull=False).select_related('product')
        product_ids = list(set(
            [e['product'] for e in wtb_entities.values('product')]))

        store_ids = [30, 61, 60, 97, 38, 9, 87, 5, 43, 23, 37, 11, 12, 18, 67,
                     167, 85, 181, 195, 197, 233, 234, 235, 236, 237, 238, 228]

        product_prices = Entity.objects.get_available().filter(
            store__in=store_ids,
            store__country=1,
            condition='https://schema.org/NewCondition',
            product__in=product_ids,
            active_registry__cell_monthly_payment__isnull=True
        ).order_by('product').values('product').annotate(
            price=Min('active_registry__offer_price')
        )

        prices_dict = {x['product']: x['price'] for x in product_prices}

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)

        titles = [
            'item_id',
            'active',
            'brand',
            'category_path',
            'category_level_1',
            'category_level_2',
            'category_level_3',
            'description',
            'image',
            'title',
            'url',
            'product_id',
            'price',
            'date_added',
            'spec_01_number',
            'spec_01_text',
            'spec_02_number',
            'spec_02_text',
            'spec_03_number',
            'spec_03_text'
        ]

        writer.writerow(titles)

        date_added = timezone.now().strftime("%Y-%m-%dT%H:%M:%S")

        for wtb_entity in wtb_entities:
            keys = wtb_entity.key.split('_')
            product_id = keys[0]
            item_id = keys[-1]

            category_level_1 = None
            category_level_2 = None
            category_level_3 = None
            category = None

            if wtb_entity.section:
                category = wtb_entity.section.replace('>', '|')
                category_levels = wtb_entity.section.split(' > ')
                category_level_count = len(category_levels)

                if category_level_count:
                    category_level_1 = category_levels[0]
                if category_level_count >= 2:
                    category_level_2 = category_levels[1]
                if category_level_count >= 3:
                    category_level_3 = category_levels[2]

            description = wtb_entity.name.replace(
                wtb_entity.model_name, '').strip()

            price = prices_dict.get(wtb_entity.product_id)

            row = [
                item_id,
                wtb_entity.is_active,
                'LG',
                category,
                category_level_1,
                category_level_2,
                category_level_3,
                description,
                wtb_entity.picture_url,
                wtb_entity.model_name,
                wtb_entity.url,
                product_id,
                price,
                date_added,
                None,
                None,
                None,
                None,
                None,
                None
            ]

            writer.writerow(row)

        return HttpResponse(
            output.getvalue(),
            content_type='text/csv'
        )

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


    @action(detail=False, methods=['get'])
    def product_entries(self, request):
        with open('lg_pricing/products.json') as f:
            json_entries = json.loads(f.read())

        products_metadata = {x['productId']: x for x in json_entries}

        store_ids = [9, 18, 11, 30]

        products = Product.objects.filter(
            pk__in=list(products_metadata.keys()))
        Product.prefetch_specs(products)
        products_dict = {p.id: p for p in products}

        entities = Entity.objects.filter(
            product__in=products,
            store__in=store_ids,
            condition='https://schema.org/NewCondition',
            active_registry__cell_monthly_payment__isnull=True
        ).get_available().order_by('active_registry__offer_price')

        result_dict = OrderedDict()

        for json_entry in json_entries:
            result_dict[products_dict[json_entry['productId']]] = []

        for product in products:
            result_dict[product] = []

        for entity in entities:
            result_dict[entity.product].append(entity)

        result_array = [{
            'product': product,
            'entities': entities
        } for product, entities in result_dict.items()]

        serializer = ProductAvailableEntitiesMinimalSerializer(
            result_array, many=True, context={'request': request})

        result = serializer.data

        for entry in result:
            entry['custom_fields'] = products_metadata[entry['product']['id']]

        return Response(result)


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
