import collections

import re
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.db import models, IntegrityError
from django.db.models import Q
from elasticsearch_dsl import Search

from metamodel.models import InstanceModel

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
    instance_model = models.ForeignKey(InstanceModel)
    creation_date = models.DateTimeField(db_index=True, auto_now_add=True)
    creator = models.ForeignKey(get_user_model())
    last_updated = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    category = property(lambda self: self.instance_model.model.category)

    def __init__(self, *args, **kwargs):
        self._specs = None
        super(Product, self).__init__(*args, **kwargs)

    @property
    def specs(self):
        if not self._specs:
            self._specs = self.es_search().filter(
                'term', product_id=self.id).execute()[0].to_dict()
        return self._specs

    @property
    def picture_url(self):
        specs = self.specs
        if 'picture' in specs:
            return default_storage.url(specs['picture'])
        return None

    def __str__(self):
        return str(self.instance_model)

    @classmethod
    def es_search(cls):
        return Search(using=settings.ES, index=settings.ES_PRODUCTS_INDEX)

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
                 doc_type=self.category.storescraper_name,
                 id=self.id,
                 body=document)

    def search_bucket_key(self, es_document):
        bucket_fields = self.category.search_bucket_key_fields
        if bucket_fields:
            return ','.join([str(es_document[field.strip()])
                             for field in bucket_fields.split(',')])
        else:
            return ''

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

    class Meta:
        app_label = 'solotodo'
        ordering = ('instance_model', )
        permissions = [
            ('backend_list_products', 'Can view product list in backend'),
        ]
