import json
import csv
import io

from django.db.models import Min
from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from sorl.thumbnail import get_thumbnail

from solotodo.models import Entity, Product
from solotodo.serializers import ProductAvailableEntitiesMinimalSerializer


class LgOnlineFeedViewSet(ViewSet):
    def list(self, request):
        with open('lg_online/products.json') as f:
            json_entries = json.loads(f.read())

        store_ids = [9, 18, 11, 5, 30, 60, 67, 37, 38, 61, 12, 85, 43, 23,
                     97, 87, 167, 86, 181, 195, 197, 224]
        product_ids = [entry['productId'] for entry in json_entries]

        product_prices = Entity.objects.get_available().filter(
            store__in=store_ids,
            product__in=product_ids,
            condition='https://schema.org/NewCondition',
            active_registry__cell_monthly_payment__isnull=True
        ).order_by('product').values('product').annotate(
            min_price=Min('active_registry__offer_price')
        )

        product_prices_dict = {
            entry['product']: entry['min_price']
            for entry in product_prices
        }

        output = io.StringIO()
        writer = csv.writer(output)

        products_dict = {
            product.id: product
            for product in Product.objects.filter(
                pk__in=product_ids).select_related(
                'instance_model__model__category')
        }

        writer.writerow([
            'id',
            'title',
            'description',
            'availability',
            'condition',
            'price',
            'link',
            'image_link',
            'brand',
            'additional_image_link',
            'google_product_category',
            'product_type'
        ])

        google_category_dict = {
            25: 'Electronics > Audio > Audio Players & Recorders',
            6: 'Electronics > Communications > Telephony > Mobile Phones',
            19: 'Home & Garden > Household Appliances > Laundry Appliances '
                '> Washing Machines',
            17: 'Home & Garden > Kitchen & Dining > Kitchen Appliances '
                '> Microwave Ovens',
            4: 'Electronics > Video > Computer Monitors',
            31: 'Electronics > Video > Projectors',
            15: 'Home & Garden > Kitchen & Dining > Kitchen Appliances '
                '> Refrigerators',
            11: 'Electronics > Video > Televisions',
        }

        for entry in json_entries:
            price = product_prices_dict.get(entry['productId'])

            if not price:
                continue

            product = products_dict[entry['productId']]

            additional_picture_urls = [
                get_thumbnail(picture.file, '1200x1200').url
                for picture in product.pictures.all()[:5]
            ]

            writer.writerow([
                product.id,
                str(product),
                entry['customDescription'] or entry['customTitle'],
                'in stock',
                'new',
                'CLP{}'.format(price.quantize(0)),
                'https://www.lgonline.cl/products/{}-{}'.format(
                    product.id, product.slug),
                get_thumbnail(product.instance_model.picture, '1200x1200').url,
                'LG',
                ','.join(additional_picture_urls),
                google_category_dict[product.category.id],
                str(product.category)
            ])

        return HttpResponse(output.getvalue())

    @action(detail=False, methods=['get'])
    def product_entries(self, request):
        with open('lg_online/products.json') as f:
            json_entries = json.loads(f.read())

        products_metadata = {x['productId']: x for x in json_entries}

        store_ids = [9, 18, 11, 5, 30, 60, 67, 37, 38, 61, 12, 85, 43, 23,
                     97, 87, 167, 86, 181, 195, 197]

        products = Product.objects.filter(
            pk__in=list(products_metadata.keys()))
        Product.prefetch_specs(products)

        entities = Entity.objects \
            .filter(
                product__in=products,
                store__in=store_ids,
                condition='https://schema.org/NewCondition',
                active_registry__cell_monthly_payment__isnull=True
            ) \
            .get_available() \
            .order_by('active_registry__offer_price')

        result_dict = {}

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
