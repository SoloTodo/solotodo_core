import json
from datetime import datetime

import pytz
from django.core.management import BaseCommand
from django.utils import dateparse, timezone

from solotodo.models import Entity, Product, Category, SoloTodoUser
from solotodo.utils import iterable_to_dict


class Command(BaseCommand):

    def handle(self, *args, **options):
        raw_associations = json.load(open('cell_associations.json', 'r'))

        associations = {tuple(key): value for key, value in raw_associations}

        entities = Entity.objects.filter(
            cell_plan_name__isnull=False).select_related()

        c = entities.count()
        u = SoloTodoUser.get_bot()

        for idx, entity in enumerate(entities):
            print('Solving: {}/{}'.format(idx+1, c))
            print('Store: {} ({})'.format(entity.store, entity.store.id))
            print('Name: {}'.format(entity.name))
            print('Cell plan name: {}'.format(entity.cell_plan_name))

            key = (entity.store.id, entity.name, entity.cell_plan_name)
            print('Key: {}'.format(key))

            value = associations.get(key)

            if not value:
                print('No match found')
                continue

            print('Found match: {}'.format(value))

            entity.product_id = value[0]
            entity.cell_plan_id = value[1]
            entity.last_association = timezone.now()
            entity.last_association_user = u
            entity.save()
