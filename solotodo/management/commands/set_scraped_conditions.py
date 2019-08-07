from django.core.management import BaseCommand

from solotodo.models import Entity


class Command(BaseCommand):
    def handle(self, *args, **options):
        entities = Entity.objects.all()

        for entity in entities:
            if entity.condition != entity.scraped_condition:
                correct_condition = entity.condition
                entity.scraped_condition = correct_condition
                entity.save()
                print(entity.id)
