import json
from dateutil import parser

import pytz
from django.core.management import BaseCommand

from guardian.shortcuts import get_anonymous_user

from solotodo.models import EntityHistory, Lead, SoloTodoUser


class Command(BaseCommand):

    def handle(self, *args, **options):
        ehs = EntityHistory.objects.filter(
            entity__product__isnull=False).select_related('entity__product')
        ehs_dict = {(eh.entity.store_id, eh.entity.product_id,
                     eh.timestamp.date()): eh for eh in ehs}

        anonymous_user = get_anonymous_user()

        users_dict = {u.id: u for u in SoloTodoUser.objects.all()}

        raw_leads = json.load(open('leads.json', 'r'))
        lead_count = len(raw_leads)

        timezone = pytz.UTC

        leads = []

        for idx, raw_lead in enumerate(raw_leads):
            print('{}/{}'.format(idx+1, lead_count))

            fields = raw_lead['fields']

            matching_eh = ehs_dict.get(
                (fields['provider'], fields['product'],
                 parser.parse(fields['date']).date())
            )

            user_id = fields['user']
            if user_id not in users_dict:
                user_id = anonymous_user.id

            if matching_eh:
                lead = Lead()
                lead.entity_history_id = matching_eh.id
                lead.timestamp = timezone.localize(
                    parser.parse(fields['timestamp']))
                lead.ip = '127.0.0.1'
                lead.user_id = user_id
                lead.website_id = 2
                leads.append(lead)

        Lead.objects.bulk_create(leads)
