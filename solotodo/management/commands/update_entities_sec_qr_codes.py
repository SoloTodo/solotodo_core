from django.core.management import BaseCommand
from django.db.models import Q

from solotodo.models import Entity
from solotodo.tasks import update_entity_sec_qr_codes


class Command(BaseCommand):
    def handle(self, *args, **options):
        es = Entity.objects.get_active().filter(
            Q(sec_qr_codes__isnull=True) | Q(sec_qr_codes='0'))
        for e in es:
            update_entity_sec_qr_codes.delay(e.id)
