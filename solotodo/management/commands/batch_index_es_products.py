import json
from decimal import Decimal

from django.core.management import BaseCommand

from metamodel.models import MetaModel, InstanceModel
from solotodo.models import Product, EsProduct


class Command(BaseCommand):
    def handle(self, *args, **options):
        filename = 'metamodel_data.json'

        print('Looking for already created metamodel dump')

        try:
            with open(filename) as f:
                print('Model found, using it. If you don\'t want to delete {} '
                      'and run the script again'.format(filename))
                d = json.load(f)
        except FileNotFoundError:
            print('No dump found, creating one and saving it in {}'.format(
                filename))
            d = MetaModel.generate_metamodel_structure()
            with open(filename, 'w') as f:
                f.write(json.dumps(d))

        for key, value in d.items():
            for field, field_value in value.items():
                if field == 'decimal_value' and field_value is not None:
                    value[field] = Decimal(field_value)

        print('Indexing products in ElasticSearch')

        products = Product.objects.all().select_related(
            'instance_model__model__category', 'brand')

        product_count = products.count()

        for idx, product in enumerate(products):
            print('{}/{} - {}'.format(idx + 1, product_count, product))
            es_document = InstanceModel.elasticsearch_document_from_dict(
                product.instance_model_id, d)

            EsProduct.from_product(product, es_document).save()
