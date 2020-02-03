import io
import csv

from django.db.models import Min
from django.utils import timezone
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError
from django.http import HttpResponse

from wtb.models import WtbEntity, WtbBrand
from solotodo.models import Entity
from solotodo.utils import format_currency

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

        entities = Entity.objects\
            .filter(product__in=products, store__in=store_ids)\
            .get_available().order_by('active_registry__offer_price')\
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
        wtb_entities = brand.wtbentity_set.select_related('product')
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
            'category',
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

            if wtb_entity.section:
                category = wtb_entity.section
                category_levels = wtb_entity.section.split(' > ')
                category_level_count = len(category_levels)
                print(category_levels)

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
