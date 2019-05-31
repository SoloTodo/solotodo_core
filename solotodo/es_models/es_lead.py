from django.conf import settings
from django.utils import timezone
from elasticsearch.helpers import bulk


class EsLead(object):
    @classmethod
    def create(cls, entity_history, website, uuid=None):
        document = {
            'uuid': uuid,
            'timestamp': timezone.now(),
            'website_id': website.id,
            'website_name': website.name,
            'normal_price': entity_history.normal_price,
            'offer_price': entity_history.offer_price,
            'normal_price_usd':
                entity_history.normal_price /
                entity_history.entity.currency.exchange_rate,
            'offer_price_usd':
                entity_history.offer_price /
                entity_history.entity.currency.exchange_rate,
            'entity_id': entity_history.entity.id,
            'entity_history_id': entity_history.id,
            'store_id': entity_history.entity.store.id,
            'store_name': entity_history.entity.store.name,
            'category_id': entity_history.entity.category.id,
            'category_name': entity_history.entity.category.name,
            'currency_id': entity_history.entity.currency.id,
            'currency_iso_code': entity_history.entity.currency.iso_code,
            'currency_name': entity_history.entity.currency.name,
            'sku': entity_history.entity.sku,
            'url': entity_history.entity.url,
            'product': entity_history.entity.product.specs,
        }

        settings.ES.index(
            index='leads',
            body=document,
            id=uuid
        )

        return document

    @classmethod
    def document_from_db_lead(cls, db_lead):
        return {
            'timestamp': db_lead.timestamp,
            'website_id': db_lead.website.id,
            'website_name': db_lead.website.name,
            'normal_price': db_lead.entity_history.normal_price,
            'offer_price': db_lead.entity_history.offer_price,
            'normal_price_usd':
                db_lead.entity_history.normal_price /
                db_lead.entity_history.entity.currency.exchange_rate,
            'offer_price_usd':
                db_lead.entity_history.offer_price /
                db_lead.entity_history.entity.currency.exchange_rate,
            'entity_id': db_lead.entity_history.entity.id,
            'entity_history_id': db_lead.entity_history.id,
            'store_id': db_lead.entity_history.entity.store.id,
            'store_name': db_lead.entity_history.entity.store.name,
            'category_id': db_lead.entity_history.entity.category.id,
            'category_name': db_lead.entity_history.entity.category.name,
            'currency_id': db_lead.entity_history.entity.currency.id,
            'currency_iso_code':
                db_lead.entity_history.entity.currency.iso_code,
            'currency_name': db_lead.entity_history.entity.currency.name,
            'sku': db_lead.entity_history.entity.sku,
            'url': db_lead.entity_history.entity.url,
            'product': db_lead.entity_history.entity.product.specs,
        }

    @classmethod
    def documents_from_db_leads(cls, db_leads):
        db_leads = db_leads.select_related(
            'website',
            'entity_history__entity__currency',
            'entity_history__entity__store',
            'entity_history__entity__category',
            'entity_history__entity__product__instance_model',
        )

        for db_lead in db_leads:
            document = cls.document_from_db_lead(db_lead)
            yield {
                '_index': 'leads',
                '_source': document
            }

    @classmethod
    def create_from_db_lead(cls, db_lead):
        es = settings.ES

        document = cls.document_from_db_lead(db_lead)

        es.index(
            index='leads',
            body=document
        )

    @classmethod
    def create_from_db_leads(cls, db_leads):
        bulk(settings.ES, cls.documents_from_db_leads(db_leads))
