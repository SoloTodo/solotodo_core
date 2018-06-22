import collections

import re

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.db import models, IntegrityError
from django.db.models import Q
from django.utils.text import slugify
from elasticsearch_dsl import Search
from sklearn.neighbors import NearestNeighbors

from metamodel.models import InstanceModel
from solotodo.models.utils import solotodo_com_site, rs_refresh_entries

from .category import Category


class ProductQuerySet(models.QuerySet):
    def filter_by_category(self, category_or_categories):
        lookup = 'instance_model__model__category'
        if isinstance(category_or_categories, collections.Iterable):
            lookup += '__in'

        return self.filter(**{lookup: category_or_categories})

    def filter_by_availability_in_countries(self, countries):
        return self.filter(
            Q(entity__active_registry__isnull=False) & ~Q(
                entity__active_registry__stock=0) & Q(
                entity__store__country__in=countries)
        ).distinct()

    def filter_by_availability_in_stores(self, stores):
        return self.filter(
            Q(entity__active_registry__isnull=False) & ~Q(
                entity__active_registry__stock=0) & Q(
                entity__store__in=stores)
        ).distinct()

    def filter_by_search_string(self, search):
        es_search = Search(using=settings.ES, index=settings.ES_PRODUCTS_INDEX)
        es_search = es_search.filter('terms', product_id=[p.id for p in self])
        es_search = Product.query_es_by_search_string(
            es_search, search, mode='AND')

        matching_product_ids = [r.product_id for r in
                                es_search[:self.count()].execute()]
        return self.filter(pk__in=matching_product_ids)

    def filter_by_user_perms(self, user, permission):
        synth_permissions = {
            'view_product': 'view_category'
        }

        assert permission in synth_permissions

        return self.filter_by_category(
            Category.objects.filter_by_user_perms(
                user, synth_permissions[permission])
        )


class Product(models.Model):
    instance_model = models.ForeignKey(InstanceModel, on_delete=models.CASCADE)
    creation_date = models.DateTimeField(db_index=True, auto_now_add=True)
    creator = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    last_updated = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    category = property(lambda self: self.instance_model.model.category)
    category_id = property(lambda self: self.instance_model.model.category.id)
    name = property(lambda self: str(self.instance_model))

    def __init__(self, *args, **kwargs):
        self._specs = None
        super(Product, self).__init__(*args, **kwargs)

    @property
    def category(self):
        return self.instance_model.model.category

    @property
    def specs(self):
        if not self._specs:
            self._specs = self.es_search().filter(
                'term', product_id=self.id).execute()[0].to_dict()
        return self._specs

    @property
    def picture_url(self):
        if 'picture' in self.specs:
            return default_storage.url(self.specs['picture'])
        return None

    @property
    def slug(self):
        return slugify(str(self))

    def __str__(self):
        return str(self.instance_model)

    @classmethod
    def es_search(cls):
        return Search(using=settings.ES, index=settings.ES_PRODUCTS_INDEX)

    @classmethod
    def prefetch_specs(cls, products):
        product_ids = [p.id for p in products]

        search = Product.es_search().filter(
            'terms', product_id=product_ids)[:len(product_ids)]
        response = search.execute().to_dict()
        specs_dict = {e['_source']['product_id']: e['_source'] for e in
                      response['hits']['hits']}

        for product in products:
            product._specs = specs_dict[product.id]

    def user_has_staff_perms(self, user):
        return user.has_perm('is_category_staff', self.category)

    def solotodo_com_url(self):
        site = solotodo_com_site()
        return 'https://{}/products/{}-{}'.format(site.domain, self.id,
                                                  slugify(str(self)))

    def save(self, *args, **kwargs):
        from django.conf import settings

        creator_id = kwargs.pop('creator_id', None)

        if bool(creator_id) == bool(self.id):
            raise IntegrityError('Exiting products cannot have a creator '
                                 '(and vice versa)')

        if creator_id:
            self.creator_id = creator_id
        super(Product, self).save(*args, **kwargs)

        es = settings.ES
        document, keywords = self.instance_model.elasticsearch_document()

        document[u'product_id'] = self.id
        document[u'keywords'] = ' '.join(keywords)
        document[u'search_bucket_key'] = self.search_bucket_key(document)

        es.index(index=settings.ES_PRODUCTS_INDEX,
                 doc_type=str(self.instance_model.model),
                 id=self.id,
                 body=document)

    def search_bucket_key(self, es_document):
        bucket_fields = self.category.search_bucket_key_fields
        if bucket_fields:
            return ','.join([str(es_document[field.strip()])
                             for field in bucket_fields.split(',')])
        else:
            return ''

    def delete_from_elasticsearch(self):
        from django.conf import settings

        es = settings.ES
        es.delete(
            index=settings.ES_PRODUCTS_INDEX,
            doc_type=str(self.instance_model.model),
            id=self.pk)

    @staticmethod
    def query_es_by_search_string(es_search, search, mode='OR'):
        from elasticsearch_dsl import Q

        search = search.strip()

        if not search:
            return es_search

        search_terms = [term.lower() for term in re.split(r'\W+', search)]
        search_query = None
        for search_term in search_terms:
            search_term_query = Q('wildcard',
                                  keywords='*{}*'.format(search_term))
            if search_query:
                if mode == 'OR':
                    search_query |= search_term_query
                else:
                    search_query &= search_term_query
            else:
                search_query = search_term_query

        return es_search.query(search_query)

    @classmethod
    def find_similar_products(cls, query_products,
                              stores=None,
                              brands=None,
                              initial_candidate_entities=None,
                              results_per_product=5):
        from solotodo.models import Entity

        if not query_products:
            return []

        category = query_products[0].category

        # Get the candidates

        if not initial_candidate_entities:
            initial_candidate_entities = Entity.objects.all()

        candidates_query = initial_candidate_entities.filter(
            product__isnull=False,
            product__instance_model__model__category=category) \
            .order_by().get_available().distinct('product') \
            .select_related('product')

        if stores is not None:
            candidates_query = candidates_query.filter(store__in=stores)

        candidates = []

        product_ids = [e.product_id for e in candidates_query]
        es_brand_products = category.es_search().filter(
            'terms', product_id=product_ids)

        if brands is not None:
            filter_parameters = {
                'brand_unicode': brands
            }
            es_brand_products = es_brand_products.filter(
                'terms', **filter_parameters)

        es_results_dict = {e.product_id: e.to_dict()
                           for e in es_brand_products[:100000].execute()}

        for entity in candidates_query:
            product = entity.product
            candidate_specs = es_results_dict.get(entity.product_id)
            if not candidate_specs:
                continue
            product._specs = candidate_specs
            candidates.append(product)

        # Obtain the (field_name, weight) pairs
        fields_metadata = []
        for field_with_weight in category.similar_products_fields.split(','):
            field_with_weight = field_with_weight.strip()

            if '**' in field_with_weight:
                field, weight_factor = field_with_weight.split('**')
                weight = 1.0 + float(weight_factor) / 10
            else:
                field = field_with_weight
                weight = 1.0

            fields_metadata.append({
                'field': field,
                'weight': weight,
                'min': Decimal('Inf'),
                'max': Decimal('-Inf'),
            })

        def attr_getter(x, field_name):
            field_value = x.get(field_name, 0)

            if field_value is None:
                return 0
            return float(field_value)

        def field_normalizer(data_entry):
            result = []
            for idx, field_value in enumerate(data_entry):
                if fields_metadata[idx]['min'] == fields_metadata[idx]['max']:
                    entry_value = 0
                else:
                    entry_value = \
                        float(field_value - fields_metadata[idx]['min']) / \
                        (fields_metadata[idx]['max'] -
                         fields_metadata[idx]['min'])
                    entry_value /= fields_metadata[idx]['weight']
                result.append(entry_value)
            return result

        candidate_entries = []
        for candidate in candidates:
            candidate_entry = []

            for entry in fields_metadata:
                field_value = attr_getter(candidate.specs, entry['field'])

                if field_value < entry['min']:
                    entry['min'] = field_value

                if field_value > entry['max']:
                    entry['max'] = field_value

                candidate_entry.append(field_value)

            candidate_entries.append(candidate_entry)

        candidate_entries = [field_normalizer(entry)
                             for entry in candidate_entries]

        if candidate_entries:
            n_neighbors = results_per_product + 1
            if n_neighbors > len(candidate_entries):
                n_neighbors = len(candidate_entries)

            neighbors = NearestNeighbors(
                n_neighbors=n_neighbors).fit(candidate_entries)

            query_entries = []
            for query_product in query_products:
                query_product_specs = query_product.specs
                query_product_entry = [
                    attr_getter(query_product_specs, entry['field'])
                    for entry in fields_metadata]
                query_entries.append(field_normalizer(query_product_entry))

            distances, indices = neighbors.kneighbors(query_entries)
        else:
            distances = [[]] * len(query_products)
            indices = [[]] * len(query_products)

        result = []
        for idx, query_product in enumerate(query_products):
            similar_products = []

            for i in range(len(indices[idx])):
                candidate = candidates[indices[idx][i]]

                if candidate != query_product:
                    similar_products.append({
                        'product': candidates[indices[idx][i]],
                        'distance': distances[idx][i]
                    })

            result.append({
                'product': query_product,
                'similar': similar_products
            })

        return result

    def find_similar(self,
                     stores=None,
                     brands=None,
                     initial_candidate_entities=None,
                     results_per_product=5):
        return self.find_similar_products(
            [self], stores=stores, brands=brands,
            initial_candidate_entities=initial_candidate_entities,
            results_per_product=results_per_product)[0]

    @classmethod
    def rs_refresh(cls):
        qs = cls.objects.select_related('instance_model__model__category')
        rs_refresh_entries(qs, 'product', 'last_updated',
                           ['id', 'name', 'creation_date',
                            'last_updated', 'category_id'])

    class Meta:
        app_label = 'solotodo'
        ordering = ('instance_model', )
        permissions = [
            ('backend_list_products', 'Can view product list in backend'),
        ]
