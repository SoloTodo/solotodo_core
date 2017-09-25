import json
from dateutil import parser

import pytz
from django.core.management import BaseCommand

from guardian.shortcuts import get_anonymous_user

from solotodo.models import EntityHistory, EntityVisit, SoloTodoUser


class Command(BaseCommand):

    def handle(self, *args, **options):
        ehs = EntityHistory.objects.filter(
            entity__product__isnull=False).select_related('entity__product')
        ehs_dict = {(eh.entity.store_id, eh.entity.product_id,
                     eh.timestamp.date()): eh for eh in ehs}

        anonymous_user = get_anonymous_user()

        users_dict = {u.id: u for u in SoloTodoUser.objects.all()}

        external_visits = json.load(open('external_visits.json', 'r'))
        external_visit_count = len(external_visits)

        timezone = pytz.timezone('America/Santiago')

        svs = []

        for idx, external_visit in enumerate(external_visits):
            print('{}/{}'.format(idx+1, external_visit_count))

            fields = external_visit['fields']

            matching_eh = ehs_dict.get(
                (fields['provider'], fields['product'],
                 parser.parse(fields['date']).date())
            )

            user_id = fields['user']
            if user_id not in users_dict:
                user_id = anonymous_user.id

            if matching_eh:
                sv = EntityVisit()
                sv.entity_history_id = matching_eh.id
                sv.timestamp = timezone.localize(
                    parser.parse(fields['timestamp']))
                sv.ip = '127.0.0.1'
                sv.user_id = user_id
                sv.api_client_id = 2
                svs.append(sv)

        EntityVisit.objects.bulk_create(svs)
