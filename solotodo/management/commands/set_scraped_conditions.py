from django.core.management import BaseCommand
from django.db.models import F

from solotodo.models import Entity


class Command(BaseCommand):
    def handle(self, *args, **options):
        entities = Entity.objects.exclude(scraped_condition=F('condition'))

        for entity in entities:
            entity.scraped_condition = entity.condition
            entity.save()
            print(entity.id)
