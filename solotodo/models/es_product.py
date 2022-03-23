from elasticsearch_dsl import Text, Keyword, Object, Integer, Date
from .es_product_entities import EsProductEntities


class EsProduct(EsProductEntities):
    product_id = Integer()
    name = Keyword()
    category_id = Integer()
    category_name = Keyword()
    brand_id = Integer()
    brand_name = Keyword()
    instance_model_id = Integer()
    creation_date = Date()
    last_updated = Date()
    keywords = Text()
    specs = Object()

    @classmethod
    def search(cls, **kwargs):
        return cls._index.search(**kwargs).filter(
            'term',
            product_relationships='product')

    @classmethod
    def category_search(cls, category, **kwargs):
        return cls.search(**kwargs).filter('term', category_id=category.id)

    @classmethod
    def get_by_product_id(cls, product_id):
        return cls.get('PRODUCT_{}'.format(product_id))

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
            instance_model_id=product.instance_model_id,
            creation_date=product.creation_date,
            last_updated=product.last_updated,
            keywords=' '.join(keywords),
            specs=specs,
            product_relationships='product',
            meta={'id': 'PRODUCT_{}'.format(product.id)}
        )
