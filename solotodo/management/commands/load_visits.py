import json
from dateutil import parser

import pytz
from django.core.management import BaseCommand

from guardian.shortcuts import get_anonymous_user

from solotodo.models import Product, Visit, SoloTodoUser


class Command(BaseCommand):

    def handle(self, *args, **options):
        products_dict = {p.id: p for p in Product.objects.all()}

        anonymous_user = get_anonymous_user()
        users_dict = {u.id: u for u in SoloTodoUser.objects.all()}

        raw_visits = json.load(open('visits.json', 'r'))
        visits_count = len(raw_visits)

        timezone = pytz.UTC

        visits = []

        for idx, raw_visit in enumerate(raw_visits):
            print('{}/{}'.format(idx+1, visits_count))

            fields = raw_visit['fields']

            matching_product = products_dict.get(fields['product'])

            user_id = fields['user']
            if user_id not in users_dict:
                user_id = anonymous_user.id

            if matching_product:
                visit = Visit()
                visit.product_id = matching_product.id
                visit.timestamp = timezone.localize(
                    parser.parse(fields['timestamp']))
                visit.ip = '127.0.0.1'
                visit.user_id = user_id
                visit.website_id = 2
                visits.append(visit)

        Visit.objects.bulk_create(visits)
