from elasticsearch_dsl import Document, Join


class EsProductEntity(Document):
    product_relationships = Join(relations={'product': 'entity'})

    @classmethod
    def _matches(cls, hit):
        # EsProductEntity is an abstract class, make sure it never gets used
        # for deserialization
        return False

    class Index:
        name = 'products_metadata'
        settings = {
            'index.mapping.total_fields.limit': 10000,
            'index.max_result_window': 100000
        }
