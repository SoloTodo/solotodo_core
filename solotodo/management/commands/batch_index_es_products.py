import json
from decimal import Decimal
from itertools import repeat
from multiprocessing import cpu_count, Pool, set_start_method
import django
django.setup()
from django.core.management import BaseCommand
from metamodel.models import MetaModel, InstanceModel
from solotodo.models import Product, EsProduct

def index_product(product, d):
    # Top level function used by multiprocessing
    print(product)
    es_document = InstanceModel.elasticsearch_document_from_dict(
        product.instance_model_id, d)

    EsProduct.from_product(product, es_document).save()

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--categories', nargs='*', type=int)

    def handle(self, *args, **options):
        filename = 'metamodel_data.json'

        print('Looking for already created metamodel dump')

        try:
            with open(filename) as f:
                print('Model found, using it. If you don\'t want to use it '
                      'then delete {} and run the script again'.format(
                            filename))
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

        category_ids = options['categories']
        if category_ids:
            products = products.filter_by_category(category_ids)

        print('Before indexing, it is a good idea to limit '
              'ElasticSearch RAM usage to 8 GB or so by creating a '
              'config/jvm.options.d/memory.options with the flags -Xms8g '
              'and -Xmx8g')
        print('Your computer has {} available cores'.format(cpu_count()))
        core_target = int(input('How many cores do you want to use for '
                                'indexing? (ideally leave 4 or so for '
                                'Elasticsearch and other stuff) '))
        print('Creating pool with {} workers'.format(core_target))
        set_start_method('spawn')
        pool = Pool(processes=core_target)
        pool.starmap(index_product, zip(products, repeat(d)))
        pool.close()
        pool.join()
