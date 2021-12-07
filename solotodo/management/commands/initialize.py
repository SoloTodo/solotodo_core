from django.conf import settings
from django.core.management import BaseCommand

from solotodo.models import EsEntity, EsProduct


class Command(BaseCommand):
    def handle(self, *args, **options):
        settings.ES.cluster.put_settings(
            body={'persistent': {'search.max_buckets': '200000'}}
        )
        EsEntity.init()
        EsProduct.init()
