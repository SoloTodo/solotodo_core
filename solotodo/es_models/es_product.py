from elasticsearch_dsl import Text, Keyword, Object, Integer, Date
from solotodo.es_models.es_product_entity import EsProductEntity


class EsProduct(EsProductEntity):
    product_id = Integer()
    name = Text(fields={'raw': Keyword()})
    category_id = Integer()
    category_name = Text(fields={'raw': Keyword()})
    brand_id = Integer()
    brand_name = Text(fields={'raw': Keyword()})
    creation_date = Date()
    last_updated = Date()
    keywords = Text()
    specs = Object()

    @classmethod
    def search(cls, **kwargs):
        return cls._index.search(**kwargs).filter('term', product_entity='product')

    @classmethod
    def from_product(cls, product, es_document=None):
        if not es_document:
            es_document = product.instance_model.elasticsearch_document()

        specs, keywords = es_document

        return cls(
            product_id=product.id,
            name=str(product),
            category_id=product.category_id,
            category_name=str(product.category),
            brand_id=product.brand_id,
            brand_name=str(product.brand),
            creation_date=product.creation_date,
            last_updated=product.last_updated,
            specs=specs,
            keywords=' '.join(keywords),
            product_entity='product',
            meta={'id': 'PRODUCT_{}'.format(product.id)}
        )
