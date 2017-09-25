import json
from datetime import datetime

import pytz
from django.core.management import BaseCommand
from django.utils import dateparse

from solotodo.models import Entity


class Command(BaseCommand):

    def handle(self, *args, **options):
        associations = json.load(open('entity_associations.json', 'r'))

        total_entity_count = len(associations)

        entities_by_url = {}
        for entity in Entity.objects.all():
            if entity.url not in entities_by_url:
                entities_by_url[entity.url] = [entity]
            else:
                entities_by_url[entity.url].append(entity)

        for idx, url in enumerate(associations):
            print('{} / {}: {}'.format(idx + 1, total_entity_count, url))

            association_data = associations[url]
            try:
                entity = entities_by_url[url]
                if len(entity) > 1:
                    print('More than one entity found for URL')
                    continue
                entity = entity[0]

                if entity.product_id == association_data['product'] \
                        and entity.cell_plan_id == association_data[
                            'secondary_product'] \
                        and entity.last_association_user_id == \
                        association_data['user']:
                    continue

                entity.product_id = association_data['product']
                entity.cell_plan_id = association_data['secondary_product']
                entity.last_association_user_id = association_data['user']
                entity.last_association = pytz.utc.localize(
                    datetime.combine(
                        dateparse.parse_date(association_data['date']),
                        datetime.min.time()))
                print('Saving entity')
                entity.save()
            except KeyError:
                print('No entity found')
                continue
