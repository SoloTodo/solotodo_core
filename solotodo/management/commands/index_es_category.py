from django.core.management import BaseCommand

from solotodo.models import Category, Product, Entity
from solotodo.tasks import product_save, entity_save

# Indexes the products and entities of the given categories in
# Elasticsearch. Requires celery workers to be running.
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--categories', nargs='*', type=int)

    def handle(self, *args, **options):
        category_ids = options['categories']
        categories = Category.objects.filter(pk__in=category_ids)

        for category in categories:
            print(category)
            ps = Product.objects.filter_by_category(category)

            # Manually test the save of a single producto to check if it
            # doesn't throw any exceptions
            if ps:
                ps[0].save()

            for p in ps:
                product_save.delay(p.id)

            es = Entity.objects.get_available().filter(
                category=category,
                product__isnull=False,
                active_registry__cell_monthly_payment__isnull=True
            )

            for e in es:
                entity_save.delay(e.id)
