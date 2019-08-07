from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.decorators import action

from wtb.models import WtbEntity
from solotodo.models import Entity

import json


class LgWtbViewSet(ViewSet):
    @action(detail=False, methods=['get'])
    def entity_data(self, request):
        params = request.GET
        product = params['product']

        store_ids = [30, 61, 60, 97, 38, 9, 87, 5, 43, 23, 37, 11, 12, 18, 67,
                     167, 85, 86, 181, 195, 197, 224]

        wtb_entities = WtbEntity.objects.filter(
            name__contains=product, brand=1)
        products = [w.product for w in wtb_entities]

        entities = Entity.objects\
            .filter(product__in=products, store__in=store_ids)\
            .get_available().order_by('active_registry__offer_price')\
            .select_related('product', 'store')

        retailers = []
        store_names = []

        for entity in entities:
            if entity.store.name in store_names:
                continue
            store_names.append(entity.store.name)
            product_images = entity.picture_urls_as_list()
            retailer = {
                "display_name": entity.store.name,
                "instock": True,
                "logo_url": entity.store.logo.url,
                "deeplink_url": entity.url,
                "price": None,
                "priceformatted": None,
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

        return Response(response)
