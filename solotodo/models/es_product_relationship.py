from elasticsearch_dsl import Document, Join


class EsProductRelationship(Document):
    product_relationships = Join(relations={'product': 'entity'})

    @classmethod
    def _matches(cls, hit):
        # EsProductRelationship is an abstract class, make sure it never
        # gets used for deserialization
        return False

    class Index:
        name = 'products_metadata'
        settings = {
            'index.mapping.total_fields.limit': 10000,
            'index.max_result_window': 200000,
            # Update this value if solotodo grows to more than 1000000 products
            'index.max_terms_count': 1000000
        }
