import json

from django.core.management import BaseCommand

from solotodo.models import Product, Brand


class Command(BaseCommand):
    def handle(self, *args, **options):
        with open('product_brands.json', 'r') as data:
            product_brands_json = json.loads(data.read())

            for idx, product in enumerate(Product.objects.all()):
                print(idx, product)
                brand_unicode = product_brands_json.get(str(product.id))
                if not brand_unicode:
                    print('Skipping:', product)
                    continue
                product.brand = Brand.objects.get_or_create(
                    name=brand_unicode)[0]
                super(Product, product).save()
