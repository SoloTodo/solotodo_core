import csv

from django.core.management import BaseCommand

from solotodo.models import Category
from wtb.models import WtbEntity, WtbBrand


class Command(BaseCommand):
    def handle(self, *args, **options):
        categories_dict = {
            "Televisor": 11
        }
        csv_reader = csv.reader(open('datos_sec.csv', 'r'), delimiter=';')

        brand = WtbBrand.objects.get(id=2)
        url = ""
        picture_url = "https://placehold.it/100x100"

        created = 0
        existing = 0

        for idx, row in enumerate(csv_reader):
            if idx == 0:
                continue

            category_key = row[1]
            category = Category.objects.get(id=categories_dict[category_key])
            p_brand = row[2]
            model = row[3]
            name = "{} {}".format(p_brand, model)

            try:
                WtbEntity.objects.get(key=model, brand=brand)
                existing += 1
            except WtbEntity.DoesNotExist:
                WtbEntity.objects.create(
                    name=name,
                    model_name=model,
                    brand=brand,
                    category=category,
                    key=model,
                    url=url,
                    picture_url=picture_url)

                created += 1

        print("{} existentes / {} creados".format(existing, created))
