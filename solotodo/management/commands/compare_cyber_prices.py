import csv
import json

from django.core.management import BaseCommand
from django.db.models import Min

from solotodo.models import Entity, Product


class Command(BaseCommand):
    def handle(self, *args, **options):
        with open('reference_prices.json') as f:
            reference_prices = json.load(f)

        reference_prices_dict = {int(key): value for key, value in
                                 reference_prices.items()}

        current_prices = Entity.objects.get_available().filter(
            active_registry__cell_monthly_payment__isnull=True,
            store__country=1,
            store__type=1,
            condition='https://schema.org/NewCondition',
            product__isnull=False
        ).order_by('product').values('product').annotate(
            normal_price=Min('active_registry__normal_price'),
            offer_price=Min('active_registry__offer_price')
        )

        product_ids = []

        for e in current_prices:
            product_ids.append(e['product'])

        products_dict = {
            x.id: x for x in Product.objects.filter(
                pk__in=product_ids).select_related(
                'instance_model__model__category')
        }

        with open('report.csv', 'w') as f:
            writer = csv.writer(f)

            writer.writerow([
                'Producto', 'Categoría', 'Precio normal anterior',
                'Precio oferta anterior', 'Precio normal Cyber',
                'Precio oferta Cyber', 'Variación precio normal',
                'Variación precio oferta'
            ])

            for e in current_prices:
                reference_prices = reference_prices_dict.get(
                    e['product'], None)
                if not reference_prices:
                    continue

                product = products_dict[e['product']]

                writer.writerow([
                    str(product),
                    str(product.category),
                    reference_prices[0],
                    reference_prices[1],
                    e['normal_price'],
                    e['offer_price'],
                    e['normal_price'] - reference_prices[0],
                    e['offer_price'] - reference_prices[1]
                ])
