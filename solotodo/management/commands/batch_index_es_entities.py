from multiprocessing import cpu_count, Pool, set_start_method
import django

django.setup()
from django.core.management import BaseCommand
from django.db import models

from solotodo.models import Entity, EsEntity


class Epoch(models.expressions.Func):
    template = "EXTRACT(epoch FROM %(expressions)s)::FLOAT"
    output_field = models.FloatField()


class DateTimeFromFloat(models.expressions.Func):
    template = "To_TIMESTAMP(%(expressions)s)::TIMESTAMP at time zone 'UTC'"
    output_field = models.DateTimeField()


def index_entity(entity, idx):
    # Top level function used by multiprocessing
    print("Entity {} ({})".format(idx, entity.id))
    EsEntity.from_entity(entity).save()


class Command(BaseCommand):
    def handle(self, *args, **options):
        # If you need to delete the previous indexed entities run the
        # following query from Kibana
        # POST /product_entities/_delete_by_query
        # {"query": {"bool": {"filter": [{"term":
        # {"product_relationships": "entity"}}]}}}

        es = (
            Entity.objects.get_available()
            .filter(
                product__isnull=False,
                active_registry__cell_monthly_payment__isnull=True,
            )
            .select_related(
                "active_registry",
                "currency",
                "bundle",
                "product__brand",
                "store__country",
                "category",
                "best_coupon",
            )
        )

        print(
            "Before indexing, it is a good idea to limit "
            "ElasticSearch RAM usage to 8 GB or so by creating a "
            "config/jvm.options.d/memory.options with the flags -Xms8g "
            "and -Xmx8g"
        )
        print("{} entities will be indexed".format(len(es)))
        print("Your computer has {} available cores".format(cpu_count()))
        core_target = int(
            input(
                "How many cores do you want to use for "
                "indexing? (ideally leave 4 or so for "
                "Elasticsearch and other stuff) "
            )
        )
        print("Creating pool with {} workers".format(core_target))
        set_start_method("spawn")
        pool = Pool(processes=core_target)
        pool.starmap(index_entity, zip(es, range(len(es))))
        pool.close()
        pool.join()
