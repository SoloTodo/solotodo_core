import json
from decimal import Decimal

from django.core.management import BaseCommand

from metamodel.models import InstanceModel
from solotodo.models import Product, Category


class Command(BaseCommand):
    def handle(self, *args, **options):
        with open('metamodel_data.json') as f:
            d = json.load(f)

        for key, value in d.items():
            for field, field_value in value.items():
                if field == 'decimal_value' and field_value is not None:
                    value[field] = Decimal(field_value)

        for category in Category.objects.all():
            print('Testing: ' + str(category))
            ps = Product.objects.filter(
                instance_model__model__category=category).order_by('?')[:20]
            for p in ps:
                print('Testing: ' + str(p))
                old_specs, old_keywords = p.instance_model.elasticsearch_document()

                old_keywords = set(old_keywords)

                # print('OLD SPECS')
                # print(json.dumps(old_specs, indent=2))

                # print('OLD KEYWORDS')
                # print(old_keywords)

                new_specs, new_keywords = InstanceModel.elasticsearch_document_from_dict(p.instance_model_id, d)
                new_keywords = set(new_keywords)

                # print('NEW SPECS')
                # print(json.dumps(new_specs, indent=2))

                # print('NEW KEYWORDS')
                # print(new_keywords)

                if old_specs != new_specs:
                    raise Exception('Spec mismatch!')

                # if old_specs == new_specs:
                #     print('SPECS MATCH!')
                # else:
                #     print('SPECS DON\'T MATCH!')

                if old_keywords != new_keywords:
                    raise Exception('Keyword mismatch!')

                # if old_keywords == new_keywords:
                #     print('KEYWORDS MATCH!')
                # else:
                #     print('KEYWORDS DON\'T MATCH!')

        # Product.batch_es_index(product_ids=[105481], metamodel_data=d)
