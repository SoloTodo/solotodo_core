from elasticsearch_dsl import Document, Join, MetaField


class EsProductEntities(Document):
    product_relationships = Join(relations={'product': 'entity'})

    @classmethod
    def _matches(cls, hit):
        # EsProductsEntities is an abstract class, make sure it never
        # gets used for deserialization
        return False

    class Meta:
        dynamic = MetaField('strict')
        dynamic_templates = MetaField([
            {
                "product_specs_keyword_fields": {
                    "path_match": "specs.*",
                    "match_mapping_type": "string",
                    "mapping": {
                        "type": "keyword"
                    }
                },
            },
            {
                "product_specs_nested_fields": {
                    "path_match": "specs.*",
                    "match_mapping_type": "object",
                    "mapping": {
                        "type": "nested"
                    }
                },
            },
        ])

    class Index:
        name = 'product_entities'
        settings = {
            'index.mapping.total_fields.limit': 10000,
            'index.max_result_window': 200000,
            # Update this value if solotodo grows to more than 1000000 products
            'index.max_terms_count': 1000000
        }
