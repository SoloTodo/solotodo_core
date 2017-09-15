import collections

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, IntegrityError
from django.db.models import Q
from elasticsearch_dsl import Search

from metamodel.models import InstanceModel


class ProductQuerySet(models.QuerySet):
    def filter_by_category(self, category):
        lookup = 'instance_model__model__category'
        if isinstance(category, collections.Iterable):
            lookup += '__in'

        return self.filter(**{lookup: category})

    def prefetch_specs(self):
        es_search = Search(using=settings.ES, index=settings.ES_PRODUCTS_INDEX)
        es_search = es_search.filter('terms', product_id=[p.id for p in self])
        es_products_dict = {
            int(e['_id']): e['_source']
            for e in es_search[:self.count()].execute().
            to_dict()['hits']['hits']}
        for product in self:
            product.SPECS_CACHE = es_products_dict[product.id]

        return self

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

    def filter_by_keywords(self, keywords):
        es_search = Search(using=settings.ES, index=settings.ES_PRODUCTS_INDEX)
        es_search = es_search\
            .filter('terms', product_id=[p.id for p in self])\
            .query('match', keywords={
                'query': keywords,
                'operator': 'and'})[:self.count()]
        matching_product_ids = [r.product_id for r in es_search.execute()]
        return self.filter(pk__in=matching_product_ids)


class Product(models.Model):
    instance_model = models.ForeignKey(InstanceModel)
    creation_date = models.DateTimeField(db_index=True, auto_now_add=True)
    creator = models.ForeignKey(get_user_model())
    last_updated = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    category = property(lambda self: self.instance_model.model.category)

    def __init__(self, *args, **kwargs):
        super(Product, self).__init__(*args, **kwargs)
        self.SPECS_CACHE = None

    @property
    def specs(self):
        if self.SPECS_CACHE is None:
            se = Search(using=settings.ES, index=settings.ES_PRODUCTS_INDEX)
            self.SPECS_CACHE = se.filter(
                'term', product_id=self.id).execute()[0].to_dict()
        return self.SPECS_CACHE

    def __str__(self):
        return str(self.instance_model)

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

        es.index(index=settings.ES_PRODUCTS_INDEX,
                 doc_type=self.category.storescraper_name,
                 id=self.id,
                 body=document)

    class Meta:
        app_label = 'solotodo'
        ordering = ('instance_model', )
        permissions = [
            ('backend_list_products', 'Can view product list in backend'),
        ]
