from datetime import timedelta
from decimal import Decimal

from django.db.models import Min
from elasticsearch_dsl import Keyword, Integer, Date, ScaledFloat
from .es_product_entities import EsProductEntities
from solotodo.models import Lead


class EsEntity(EsProductEntities):
    entity_id = Integer()
    store_id = Integer()
    store_name = Keyword()
    category_id = Integer()
    category_name = Keyword()
    currency_id = Integer()
    currency_name = Keyword()
    condition = Keyword()
    product_id = Integer()
    product_name = Keyword()
    bundle_id = Integer()
    bundle_name = Keyword()
    brand_id = Integer()
    brand_name = Keyword()
    country_id = Integer()
    country_name = Keyword()

    normal_price = ScaledFloat(scaling_factor=100)
    offer_price = ScaledFloat(scaling_factor=100)
    normal_price_usd = ScaledFloat(scaling_factor=100)
    offer_price_usd = ScaledFloat(scaling_factor=100)

    reference_normal_price = ScaledFloat(scaling_factor=100)
    reference_offer_price = ScaledFloat(scaling_factor=100)
    reference_normal_price_usd = ScaledFloat(scaling_factor=100)
    reference_offer_price_usd = ScaledFloat(scaling_factor=100)

    normal_price_per_unit = ScaledFloat(scaling_factor=100)
    offer_price_per_unit = ScaledFloat(scaling_factor=100)
    normal_price_usd_per_unit = ScaledFloat(scaling_factor=100)
    offer_price_usd_per_unit = ScaledFloat(scaling_factor=100)

    name = Keyword()
    part_number = Keyword()
    sku = Keyword()
    key = Keyword()
    url = Keyword()

    leads = Integer()

    creation_date = Date()
    last_updated = Date()

    @classmethod
    def search(cls, **kwargs):
        return cls._index.search(**kwargs).exclude(
            'term',
            product_relationships='product')

    @classmethod
    def get_by_entity_id(cls, entity_id):
        return cls.get('ENTITY_{}'.format(entity_id))

    @classmethod
    def should_entity_be_indexed(cls, entity):
        return entity.is_available() and entity.product and \
               entity.active_registry.cell_monthly_payment is None

    @classmethod
    def from_entity(cls, entity, prices_dict=None, leads_dict=None):
        from django.conf import settings

        assert cls.should_entity_be_indexed(entity)
        active_registry = entity.active_registry

        timestamp = active_registry.timestamp

        if prices_dict:
            reference_prices = prices_dict.get(entity.id)
            if reference_prices:
                reference_normal_price, reference_offer_price = reference_prices
            else:
                reference_normal_price = active_registry.normal_price
                reference_offer_price = active_registry.offer_price
        else:
            reference_prices = entity.entityhistory_set.filter(
                timestamp__gte=timestamp - timedelta(hours=84),
                timestamp__lte=timestamp - timedelta(hours=36)
            ).aggregate(
                min_normal_price=Min('normal_price'),
                min_offer_price=Min('offer_price')
            )

            reference_normal_price = reference_prices['min_normal_price'] or \
                active_registry.normal_price
            reference_offer_price = reference_prices['min_offer_price'] or \
                active_registry.offer_price

        if leads_dict:
            leads = leads_dict.get(entity.id, 0)
        else:
            leads = Lead.objects.filter(
                entity_history__entity=entity,
                timestamp__gte=timestamp - timedelta(hours=72)
            ).count()

        if entity.bundle:
            bundle_name = entity.bundle.name
            bundle_id = entity.bundle.id
        else:
            bundle_name = None
            bundle_id = None

        exchange_rate = entity.currency.exchange_rate
        normal_price_usd = entity.active_registry.normal_price / exchange_rate
        offer_price_usd = entity.active_registry.offer_price / exchange_rate

        if entity.category_id == settings.GROCERIES_CATEGORY_ID:
            # entity.product is not null because only associated entities
            # can be indexed
            specs = entity.product.specs
            conversion_factor = \
                Decimal(specs['category_unit_price_per_unit_conversion_factor']) / \
                Decimal(specs['volume_weight'])

            normal_price_per_unit = (active_registry.normal_price * conversion_factor).quantize(0)
            offer_price_per_unit = (active_registry.offer_price * conversion_factor).quantize(0)
            normal_price_usd_per_unit = (normal_price_usd * conversion_factor).quantize(Decimal('0.01'))
            offer_price_usd_per_unit = (offer_price_usd * conversion_factor).quantize(Decimal('0.01'))
        else:
            normal_price_per_unit = active_registry.normal_price
            offer_price_per_unit = active_registry.offer_price
            normal_price_usd_per_unit = normal_price_usd
            offer_price_usd_per_unit = offer_price_usd

        return cls(
            entity_id=entity.id,
            store_id=entity.store_id,
            store_name=str(entity.store),
            category_id=entity.category_id,
            category_name=str(entity.category),
            currency_id=entity.currency_id,
            currency_name=str(entity.currency),
            condition=entity.condition,
            product_id=entity.product_id,
            product_name=str(entity.product),
            bundle_id=bundle_id,
            bundle_name=bundle_name,
            brand_id=entity.product.brand_id,
            brand_name=str(entity.product.brand),
            country_id=entity.store.country_id,
            country_name=str(entity.store.country),
            normal_price=active_registry.normal_price,
            offer_price=active_registry.offer_price,
            normal_price_usd=normal_price_usd,
            offer_price_usd=offer_price_usd,
            reference_normal_price=reference_normal_price,
            reference_offer_price=reference_offer_price,
            reference_normal_price_usd=reference_normal_price / exchange_rate,
            reference_offer_price_usd=reference_offer_price / exchange_rate,
            normal_price_per_unit=normal_price_per_unit,
            offer_price_per_unit=offer_price_per_unit,
            normal_price_usd_per_unit=normal_price_usd_per_unit,
            offer_price_usd_per_unit=offer_price_usd_per_unit,
            name=entity.name,
            part_number=entity.part_number,
            sku=entity.sku,
            key=entity.key,
            url=entity.url,
            leads=leads,
            creation_date=entity.creation_date,
            last_updated=entity.last_updated,
            product_relationships={
                'name': 'entity',
                'parent': 'PRODUCT_{}'.format(entity.product_id)
            },
            meta={'id': 'ENTITY_{}'.format(entity.id)}
        )

    @classmethod
    def get_by_entity_id(cls, entity_id):
        return cls.get('ENTITY_{}'.format(entity_id))

    def save(self, **kwargs):
        self.meta.routing = 'PRODUCT_{}'.format(self.product_id)
        return super(EsEntity, self).save(**kwargs)
