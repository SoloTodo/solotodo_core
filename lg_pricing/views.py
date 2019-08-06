from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.decorators import action

from solotodo.models import Entity

import json


class LgWtbViewSet(ViewSet):
    @action(detail=False, methods=['get'])
    def entity_data(self, request):
        params = request.GET
        product = params['product']
        callback = params['callback']

        entities = Entity.objects.filter(name__contains=product)\
            .get_available()

        retailers = []
        store_names = []

        for entity in entities:
            if entity.store.name in store_names:
                continue
            store_names.append(entity.store.name)
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
                "product_images": json.loads(entity.picture_urls)
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
