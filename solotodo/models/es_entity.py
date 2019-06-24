from datetime import timedelta
from django.db.models import Min
from elasticsearch_dsl import Text, Keyword, Integer, Date, ScaledFloat
from .es_product_relationship import EsProductRelationship
from solotodo.models import Lead


class EsEntity(EsProductRelationship):
    entity_id = Integer()
    store_id = Integer()
    store_name = Text(fields={'raw': Keyword()})
    category_id = Integer()
    category_name = Text(fields={'raw': Keyword()})
    currency_id = Integer()
    currency_name = Text(fields={'raw': Keyword()})
    condition = Keyword()
    product_id = Integer()
    product_name = Text(fields={'raw': Keyword()})
    brand_id = Integer()
    brand_name = Text(fields={'raw': Keyword()})
    country_id = Integer()
    country_name = Text(fields={'raw': Keyword()})

    normal_price = ScaledFloat(scaling_factor=100)
    offer_price = ScaledFloat(scaling_factor=100)
    normal_price_usd = ScaledFloat(scaling_factor=100)
    offer_price_usd = ScaledFloat(scaling_factor=100)

    reference_normal_price = ScaledFloat(scaling_factor=100)
    reference_offer_price = ScaledFloat(scaling_factor=100)
    reference_normal_price_usd = ScaledFloat(scaling_factor=100)
    reference_offer_price_usd = ScaledFloat(scaling_factor=100)

    name = Text(fields={'raw': Keyword()})
    part_number = Text(fields={'raw': Keyword()})
    sku = Text(fields={'raw': Keyword()})
    key = Text(fields={'raw': Keyword()})
    url = Text(fields={'raw': Keyword()})

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
    def from_entity(cls, entity):
        assert cls.should_entity_be_indexed(entity)

        timestamp = entity.active_registry.timestamp

        reference_prices = entity.entityhistory_set.filter(
            timestamp__gte=timestamp - timedelta(hours=84),
            timestamp__lte=timestamp - timedelta(hours=36)
        ).aggregate(
            min_normal_price=Min('normal_price'),
            min_offer_price=Min('offer_price')
        )

        reference_normal_price = reference_prices['min_normal_price'] or \
            entity.active_registry.normal_price
        reference_offer_price = reference_prices['min_offer_price'] or \
            entity.active_registry.offer_price

        exchange_rate = entity.currency.exchange_rate

        leads = Lead.objects.filter(
            entity_history__entity=entity,
            timestamp__gte=timestamp - timedelta(hours=72)
        ).count()

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
            brand_id=entity.product.brand_id,
            brand_name=str(entity.product.brand),
            country_id=entity.store.country_id,
            country_name=str(entity.store.country),
            normal_price=entity.active_registry.normal_price,
            offer_price=entity.active_registry.offer_price,
            normal_price_usd=entity.active_registry.normal_price /
            exchange_rate,
            offer_price_usd=entity.active_registry.offer_price /
            exchange_rate,
            reference_normal_price=reference_normal_price,
            reference_offer_price=reference_offer_price,
            reference_normal_price_usd=reference_normal_price / exchange_rate,
            reference_offer_price_usd=reference_offer_price / exchange_rate,
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

    def save(self, **kwargs):
        self.meta.routing = 'PRODUCT_{}'.format(self.product_id)
        return super(EsEntity, self).save(**kwargs)
