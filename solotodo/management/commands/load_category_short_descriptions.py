from django.core.management import BaseCommand

from category_templates.models import CategoryTemplate
from solotodo.models import Entity
from solotodo.tasks import entity_save


class Command(BaseCommand):
    def handle(self, *args, **options):
        templates = CategoryTemplate.objects.filter(
            website=2,
            purpose=3
        )
        for template in templates:
            template.category.browse_result_template = template.body
            template.category.save()

        templates = CategoryTemplate.objects.filter(
            website=2,
            purpose=1
        )
        for template in templates:
            template.category.detail_template = template.body
            template.category.save()
