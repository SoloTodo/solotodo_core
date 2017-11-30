import json
from datetime import datetime

import pytz
from django.core.management import BaseCommand
from django.utils import dateparse

from solotodo.models import Entity, Product, Category, Store
from solotodo.utils import iterable_to_dict


class Command(BaseCommand):

    def handle(self, *args, **options):
        associations = json.load(open('entity_associations_by_name.json', 'r'))

        products_dict = iterable_to_dict(Product, 'id')
        stores_dict = iterable_to_dict(Store, 'id')

        for key, payload in associations:
            store_id, entity_name = key
            store = stores_dict[store_id]

            print('Finding entity with key: {} - {}'.format(store,
                                                            entity_name))
            entities = Entity.objects.filter(store=store, name=entity_name)

            match_count = entities.count()

            if match_count == 0:
                print('No entity found')
                continue
            elif match_count > 1:
                print('More than one entity found')
                for entity in entities:
                    print('* {} - {}'.format(entity.id, entity.url))
                continue

            entity = entities[0]
            print('Matching entity found: {}'.format(entity.id))

            product_id = payload['product']
            product = products_dict.get(product_id, None)

            if not product:
                print('No matching product found: {}'.format(product_id))

            secondary_product_id = payload['secondary_product']

            if secondary_product_id:
                secondary_product = products_dict.get(
                    secondary_product_id, None)
                if not secondary_product:
                    print('No matching secondary product found: {}'.format(
                        product_id))
            else:
                secondary_product = None

            entity.product_type_id = payload['product_type']
            entity.product = product
            entity.cell_plan = secondary_product
            entity.last_association = pytz.utc.localize(
                    datetime.combine(
                        dateparse.parse_date(payload['date']),
                        datetime.min.time()))
            entity.last_association_user_id = payload['user']
            entity.save()
