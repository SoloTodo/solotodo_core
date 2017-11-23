import json

from django.core.management import BaseCommand
from django.utils import timezone

from solotodo.models import Product, SoloTodoUser
from wtb.models import WtbEntity


class Command(BaseCommand):

    def handle(self, *args, **options):
        associations = json.load(open('wtb_associations.json', 'r'))

        u = SoloTodoUser.objects.get(pk=507)
        now = timezone.now()

        for entity_url, product_id in associations.items():
            print('Anlyzing: {} - {}'.format(entity_url, product_id))

            try:
                wtb_entity = WtbEntity.objects.get(url=entity_url)
                print('Entity found: {}'.format(wtb_entity))
            except WtbEntity.DoesNotExist:
                print('No matching entity found')
                continue

            try:
                product = Product.objects.get(pk=product_id)
                print('Product found: {}'.format(product))
            except Product.DoesNotExist:
                print('No matching product found')
                continue

            wtb_entity.product = product
            wtb_entity.last_association = now
            wtb_entity.last_association_user = u

            wtb_entity.save()
            print('Associated')
