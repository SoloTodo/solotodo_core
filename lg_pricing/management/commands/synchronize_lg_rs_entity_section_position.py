from django.core.mail import send_mail
from django.core.management import BaseCommand

from lg_pricing.models import LgRsEntitySectionPosition


class Command(BaseCommand):
    def handle(self, *args, **options):
        send_mail('Starting position sync', 'Started', 'solobot@solotodo.com',
                  ['vj@solotodo.com'])
        LgRsEntitySectionPosition.synchronize_with_db_positions()
        send_mail('Finished position sync', 'Started', 'solobot@solotodo.com',
                  ['vj@solotodo.com'])
