from django.core.management import BaseCommand

from solotodo.models import Entity
from solotodo.tasks import update_entity_sec_qr_codes


class Command(BaseCommand):
    def handle(self, *args, **options):
        es = Entity.objects.get_active().filter(sec_qr_codes__isnull=True)
        for e in es:
            update_entity_sec_qr_codes.delay(e.id)
