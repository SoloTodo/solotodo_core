import datetime
import json

from django.core.management import BaseCommand
from django.db.models import Min

from solotodo.models import EntityHistory


class Command(BaseCommand):
    def handle(self, *args, **options):
        start_date = datetime.date(2022, 3, 9)
        end_date = datetime.date(2022, 5, 23)

        best_product_prices = EntityHistory.objects.filter(
            entity__active_registry__cell_monthly_payment__isnull=True,
            entity__store__country=1,
            entity__store__type=1,
            entity__condition='https://schema.org/NewCondition',
            entity__product__isnull=False,
            timestamp__gte=start_date,
            timestamp__lt=end_date
        ).exclude(stock=0).order_by('entity__product')\
            .values('entity__product')\
            .annotate(
                normal_price=Min('normal_price'),
                offer_price=Min('offer_price')
            )

        best_product_prices_dict = {}

        for best_product_price_entry in best_product_prices:
            best_product_prices_dict[
                str(best_product_price_entry['entity__product'])
            ] = [int(best_product_price_entry['normal_price']),
                 int(best_product_price_entry['offer_price'])]

        with open('reference_prices.json', 'w') as f:
            f.write(json.dumps(best_product_prices_dict))
