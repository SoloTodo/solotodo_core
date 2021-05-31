import json

from django.core.management import BaseCommand

from solotodo.models import Entity, Country


class Command(BaseCommand):
    def handle(self, *args, **options):
        with open('reference_prices.json') as f:
            reference_prices = json.load(f)

        reference_prices_dict = {int(key): value for key, value in
                                 reference_prices.items()}
        c = Country.objects.get(name='Chile')
        current_prices = Entity.objects.get_available().filter(
            active_registry__cell_monthly_payment__isnull=True,
            store__country=c,
            condition='https://schema.org/NewCondition',
            product__isnull=False
        ).select_related(
            'store', 'active_registry', 'product__instance_model',
            'category'
        )

        with open('report.csv', 'w') as f:
            print('Tienda', 'Producto', 'Categoría', 'Precio normal anterior',
                  'Precio oferta anterior', 'Precio normal Cyber',
                  'Precio oferta Cyber', 'Variación precio normal',
                  'Variación precio oferta', file=f, sep='¬')

            for e in current_prices:
                reference_prices = reference_prices_dict.get(e.id, None)
                if not reference_prices:
                    continue

                print(e.store, e.product, e.category, reference_prices[0],
                      reference_prices[1],  e.active_registry.normal_price,
                      e.active_registry.offer_price,
                      e.active_registry.normal_price - reference_prices[0],
                      e.active_registry.offer_price - reference_prices[1],
                      file=f, sep='¬')
