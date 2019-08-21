from collections import defaultdict
from decimal import Decimal

from django.contrib.auth.models import Group
from guardian.shortcuts import get_objects_for_group

from solotodo.models import Store, Entity


class PcFactorySkuAnalysisForm:
    @classmethod
    def generate_report(cls):
        store = Store.objects.get(name='PC Factory')
        group = Group.objects.get(name='PC Factory')

        stores = get_objects_for_group(group, 'view_store', Store)
        pcf_entities = store.entity_set.filter(
            product__isnull=False
        ).get_available().select_related(
            'active_registry',
            'product__instance_model__model__category'
        )

        product_ids = [e['product_id'] for e in
                       pcf_entities.values('product_id')]

        stores_entities = Entity.objects.filter(
            store__in=stores,
            product__in=product_ids,
            condition='https://schema.org/NewCondition',
            active_registry__cell_monthly_payment__isnull=True,
            store__type=1
        ).get_available().select_related('store', 'active_registry').order_by(
            'product',
            'active_registry__normal_price'
        )

        product_entities_dict = defaultdict(lambda: [])

        for e in stores_entities:
            product_entities_dict[e.product_id].append(e)

        result = []

        for pcf_entity in pcf_entities:
            pcf_price = pcf_entity.active_registry.normal_price

            product_entities = product_entities_dict[pcf_entity.product_id]

            min_normal_price = product_entities[0].active_registry.normal_price
            median_normal_price = product_entities[
                len(product_entities) // 2].active_registry.normal_price

            normal_price_delta = \
                Decimal('100') * (pcf_price - min_normal_price) / \
                min_normal_price

            entry = {
                'sku': pcf_entity.sku,
                'product': str(pcf_entity.product),
                'category': str(pcf_entity.product.category),
                'pcf_normal_price': pcf_price,
                'min_normal_price': min_normal_price,
                'normal_price_delta': normal_price_delta,
                'median_normal_price': median_normal_price,
                'store_prices': []
            }

            for entity in product_entities:
                entry['store_prices'].append({
                    'store': str(entity.store),
                    'sku': str(entity.sku),
                    'url': str(entity.url),
                    'normal_price': str(entity.active_registry.normal_price)
                })

            result.append(entry)

        return result
