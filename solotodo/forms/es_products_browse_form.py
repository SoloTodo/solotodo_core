import json
from collections import OrderedDict

import re
from django import forms
from django.conf import settings
from django.db.models import Min, F, Sum, Value
from django.db.models.functions import Coalesce
from elasticsearch_dsl import A, Q

from solotodo.filters import ProductsBrowseEntityFilterSet, \
    CategoryFullBrowseEntityFilterSet
from solotodo.models import Country, Product, Currency, CategorySpecsFilter, \
    Entity, Store, Category, Brand
from solotodo.pagination import ProductsBrowsePagination
from solotodo.serializers import CategoryBrowseResultSerializer, \
    CategoryFullBrowseResultSerializer
from solotodo.utils import iterable_to_dict


class EsProductsBrowseForm(forms.Form):
    stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all(),
        required=False
    )
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False
    )
    countries = forms.ModelMultipleChoiceField(
        queryset=Country.objects.all(),
        required=False
    )
    products = forms.ModelMultipleChoiceField(
        queryset=Product.objects.all(),
        required=False
    )
    entities = forms.ModelMultipleChoiceField(
        queryset=Entity.objects.all(),
        required=False
    )
    db_brands = forms.ModelMultipleChoiceField(
        queryset=Brand.objects.all(),
        required=False
    )
    normal_price_0 = forms.DecimalField(required=False)
    normal_price_1 = forms.DecimalField(required=False)
    offer_price_0 = forms.DecimalField(required=False)
    offer_price_1 = forms.DecimalField(required=False)
    normal_price_usd_0 = forms.DecimalField(required=False)
    normal_price_usd_1 = forms.DecimalField(required=False)
    offer_price_usd_0 = forms.DecimalField(required=False)
    offer_price_usd_1 = forms.DecimalField(required=False)

    PRICING_ORDERING_CHOICES = [
        'normal_price',
        'offer_price',
        'normal_price_usd',
        'offer_price_usd',
    ]
    DEFAULT_ORDERING = 'offer_price'

    DB_ORDERING_CHOICES = PRICING_ORDERING_CHOICES + ['leads', 'discount']

    ordering = forms.CharField(required=False)
    search = forms.CharField(required=False)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(EsProductsBrowseForm, self).__init__(*args, **kwargs)

    def clean_stores(self):
        stores = self.cleaned_data['stores']

        if stores:
            for store in stores:
                if not self.user.has_perm('view_store', store):
                    raise forms.ValidationError(
                        'Unauthorized store ID: {}'.format(store.id))

        return stores

    def clean_categories(self):
        categories = self.cleaned_data['categories']

        if categories:
            for category in categories:
                if not self.user.has_perm('view_category', category):
                    raise forms.ValidationError(
                        'Unauthorized category ID: {}'.format(category.id))

        return categories

    def clean_products(self):
        products = self.cleaned_data['products']

        if products:
            for product in products.select_related('instance_model__model__category'):
                if not self.user.has_perm('view_category', product.category):
                    raise forms.ValidationError(
                        'Invalid product ID due to unauthorized category: {}'
                        ''.format(product.id))

        return products

    def clean_entities(self):
        entities = self.cleaned_data['entities']

        if entities:
            for entity in entities.select_related('store', 'category'):
                if not self.user.has_perm('view_store', entity.store):
                    raise forms.ValidationError(
                        'Invalid entity ID due to unauthorized store: {}'
                        ''.format(entity.id))

        return entities

    def get_category_entities(self, category, request):
        """
        Returns the available entities of queried products
        """
        from category_columns.models import CategoryColumn

        assert self.is_valid()

        # 1. Filtering and annotation of entities
        entities = CategoryFullBrowseEntityFilterSet.get_entities(
            request, category)

        query_params = request.query_params.copy()
        query_params.pop('ordering', None)

        # 2. Create ES search that filters based on technical terms.
        # Also calculates the aggregation count for the form filters

        product_ids = set(entry['product']
                          for entry in entities.values('product'))
        es_search = category.es_search().filter(
            'terms', product_id=list(product_ids))

        specs_form_class = category.specs_form()
        specs_form = specs_form_class(query_params)

        es_results = specs_form.get_es_products(
            es_search)[:len(product_ids)].execute()

        filtered_product_ids = [entry['product_id'] for entry in es_results]
        entities = entities.filter(product__in=filtered_product_ids)

        # 3. Obtain filter aggs
        filter_aggs = specs_form.process_es_aggs(es_results.aggs)

        # 4. Bucket the results in (product, cell_plan) pairs, also calculate
        # the price ranges
        bucketed_entities_dict = OrderedDict()
        normal_prices_usd = []
        offer_prices_usd = []

        for entity in entities:
            normal_prices_usd.append(entity.normal_price_usd)
            offer_prices_usd.append(entity.offer_price_usd)

            key = (entity.product, entity.cell_plan)
            if key not in bucketed_entities_dict:
                bucketed_entities_dict[key] = []

            bucketed_entities_dict[key].append(entity)

        normal_prices_usd.sort()
        offer_prices_usd.sort()

        entity_count = len(normal_prices_usd)

        if entity_count:
            price_ranges = {
                'normal_price_usd': {
                    'min': normal_prices_usd[0],
                    'max': normal_prices_usd[-1],
                    '80th': normal_prices_usd[int(entity_count * 0.8)]
                },
                'offer_price_usd': {
                    'min': offer_prices_usd[0],
                    'max': offer_prices_usd[-1],
                    '80th': offer_prices_usd[int(entity_count * 0.8)]
                },
            }
        else:
            price_ranges = None

        # 5. Serialization
        bucketed_results = [{
            'product': key[0],
            'cell_plan': key[1],
            'entities': value
        } for key, value in bucketed_entities_dict.items()]

        specs_columns = CategoryColumn.objects.filter(
            field__category=category,
            purpose=settings.CATEGORY_PURPOSE_BROWSE_ID
        ).select_related('field')

        desired_spec_fields = \
            ['brand_unicode'] + \
            [column.field.es_field for column in specs_columns]

        serialized_data = CategoryFullBrowseResultSerializer(
            bucketed_results, many=True, context={'request': request}
        ).data

        for serialized_entry in serialized_data:
            spec_fields = list(serialized_entry['product']['specs'].keys())

            for spec_field in spec_fields:
                if spec_field not in desired_spec_fields:
                    del serialized_entry['product']['specs'][spec_field]

        return {
            'aggs': filter_aggs,
            'results': serialized_data,
            'price_ranges': price_ranges,
            'entities': entities
        }

    def get_products(self, request):
        if not self.is_valid():
            return self.errors

        # 1. Filtering and aggregation of entities
        entities = self.initial_entities(request).filter(
            product__isnull=False
        )

        ordering = self.cleaned_data.get('ordering', self.DEFAULT_ORDERING)

        # 3. DB ordering (if it applies)
        if ordering in self.DB_ORDERING_CHOICES:
            # The same parameters will be passed to the specs form, and there
            # the DB ordering choices are invalid, so pop them.
            entities = self.order_entities_by_db(entities, ordering)

        product_ids = [entry['product'] for entry in entities]

        es_search = Product.es_search().filter(
            'terms', product_id=product_ids)

        search = self.cleaned_data['search']
        if search:
            es_search = Product.query_es_by_search_string(
                es_search, search, mode='OR')

        if search:
            es_results = es_search[:len(product_ids)].execute()
            filtered_product_ids = [entry['product_id']
                                    for entry in es_results]
            entities = entities.filter(product__in=filtered_product_ids)
        else:
            es_results = es_search[:len(product_ids)].execute()

        # 6. Get the min, max, and 80th percentile normal and offer price
        price_ranges = self.entities_price_ranges(entities)

        # 7. Obtain price entries and bucket the results

        bucketed_results = self.bucket_results(entities, es_results)

        # 8. Paginate

        bucketed_results_page = self.paginate_bucketed_results(
            request, bucketed_results)

        # 9. Serialization

        serializer = self.serialize_results(request, bucketed_results_page)

        return {
            'count': len(bucketed_results),
            'results': serializer.data,
            'price_ranges': price_ranges
        }

    def get_category_products(self, category, request):
        from solotodo.es_models import EsProduct

        assert self.is_valid()

        search = EsProduct.search().filter('term', category_id=category.id)

        # 1. Filter entities based on our form fields
        search = self.filter_entities(search)

        specs_query_params = request.query_params.copy()

        # Pop out the ordering from the query params that will be passed to
        # the specs form if it will be resolved by us
        if self.cleaned_data['ordering'] in self.DB_ORDERING_CHOICES:
            # The same parameters will be passed to the specs form, and there
            # the DB ordering choices are invalid, so pop them.
            specs_query_params.pop('ordering', None)

        # 2. Filter based on technical terms. Also calculates the
        # aggregation count for the form filters

        specs_form_class = category.specs_form(form_type='es')
        specs_form = specs_form_class(specs_query_params)

        search = specs_form.get_es_products(search)

        # 3. Add the metrics
        product_stats_bucket = A('terms', field='product_id', size=10000)
        for pricing_field in ['normal_price', 'offer_price', 'normal_price_usd', 'offer_price_usd', 'reference_normal_price', 'reference_offer_price', 'reference_normal_price_usd', 'reference_offer_price_usd']:
            product_stats_bucket.metric(pricing_field, 'min', field=pricing_field)
        product_stats_bucket.metric('leads', 'sum', field='leads')

        search.aggs.bucket('product_prices', product_stats_bucket)

        es_result = search.execute()

        return es_result.to_dict()

        # 5. Obtain filter aggs
        filter_aggs = specs_form.process_es_aggs(es_result.aggs)

        # 7. Obtain price entries and bucket the results

        bucket_field = specs_form.cleaned_data['bucket_field']
        bucketed_results = self.bucket_results(
            entities, es_results, bucket_field)

        # 8. Paginate

        bucketed_results_page = self.paginate_bucketed_results(
            request, bucketed_results)

        # 9. Serialization

        serializer = self.serialize_results(request, bucketed_results_page)

        return {
            'count': len(bucketed_results),
            'aggs': filter_aggs,
            'results': serializer.data,
            'price_ranges': price_ranges
        }

    def get_share_of_shelves(self, category, request):
        data = self.get_category_entities(category, request)
        product_ids = [p['product']['id'] for p in data['results']]
        entities_agg = {}

        es_search = Product.es_search().filter('terms', product_id=product_ids)
        es_dict = {e.product_id: e.to_dict()
                   for e in es_search[:len(product_ids)].execute()}

        query_params = request.query_params.copy()
        bucketing_field = query_params.get('bucketing_field')

        spec_filters = CategorySpecsFilter.objects.filter(
            category=category,
            name=bucketing_field)

        if not spec_filters:
            raise KeyError

        spec_filter = spec_filters[0]

        if spec_filter.meta_model.is_primitive():
            es_field = spec_filter.es_field
        else:
            es_field = spec_filter.es_field + '_unicode'

        for p in data['results']:
            product_id = p['product']['id']
            es_entry = es_dict[product_id]

            key = es_entry[es_field]

            if isinstance(key, bool):
                key = 'Sí' if key else 'No'

            if key in entities_agg:
                entities_agg[key] += len(p['entities'])
            else:
                entities_agg[key] = len(p['entities'])

        result = []

        for key, count in entities_agg.items():
            result.append({
                "label": key,
                "doc_count": count,
            })

        result = sorted(result, key=lambda k: k['doc_count'], reverse=True)

        return {
            "aggs": data['aggs'],
            "results": result,
            "price_ranges": data['price_ranges']
        }

    def filter_entities(self, search):
        filter_fields = [
            ('stores', 'store_id'),
            ('categories', 'category_id'),
            ('countries', 'country_id'),
            ('products', 'product_id'),
            ('entities', 'entity_id'),
            ('db_brands', 'brand_id'),
        ]

        entities_filter = Q()

        for field_name, es_field in filter_fields:
            if self.cleaned_data[field_name]:
                entities_filter &= Q('terms', **{es_field: [x.id for x in self.cleaned_data[field_name]]})

        range_fields = ['normal_price', 'offer_price', 'normal_price_usd', 'offer_price_usd']

        for range_field in range_fields:
            start_value = self.cleaned_data[range_field + '_0']
            end_value = self.cleaned_data[range_field + '_1']

            range_params = {}

            if start_value:
                range_params['gte'] = start_value
            if end_value:
                range_params['lte'] = end_value

            if range_params:
                entities_filter &= Q('range', **{range_field: range_params})

        return search.filter('has_child', type='entity', query=entities_filter)

    def order_entities_by_db(self, entities, ordering):
        if ordering in self.PRICING_ORDERING_CHOICES:
            ordering_field = 'min_' + ordering
            return entities.order_by(
                ordering_field, 'product', 'currency')
        elif ordering == 'leads':
            return entities \
                .order_by('-leads', 'product', 'currency')
        elif ordering == 'discount':
            return entities \
                .annotate(discount=Coalesce(
                    F('min_reference_offer_price_usd') -
                    F('min_offer_price_usd'),
                    Value(0)))\
                .order_by('-discount', 'product', 'currency')
        else:
            raise Exception('This condition is unreachable')

    def product_prices_dict(self, entities):
        product_id_to_prices = {}

        currencies_dict = iterable_to_dict(Currency)

        for entry in entities:
            currency = currencies_dict[entry['currency']]
            product_id = entry['product']

            entry_prices = {
                'currency': currency,
                'min_normal_price': entry['min_normal_price'],
                'min_offer_price': entry['min_offer_price'],
                'min_normal_price_usd': entry['min_normal_price_usd'],
                'min_offer_price_usd': entry['min_offer_price_usd'],
            }

            if product_id in product_id_to_prices:
                product_id_to_prices[product_id].append(entry_prices)
            else:
                product_id_to_prices[product_id] = [entry_prices]

        return product_id_to_prices

    def bucket_results(self, entities, es_results, bucket_field='product_id'):
        ordering = self.ordering_or_default()
        product_id_to_prices = self.product_prices_dict(entities)

        product_ids = [entity['product'] for entity in entities]

        product_id_to_specs = {
            entry['_source']['product_id']: entry['_source']
            for entry in es_results.to_dict()['hits']['hits']
        }

        product_id_to_instance = iterable_to_dict(
            Product.objects.filter(pk__in=product_ids).select_related(
                'instance_model__model__category'))

        product_id_to_full_instance = {}
        for product_id in product_ids:
            full_instance = product_id_to_instance[product_id]
            full_instance._specs = product_id_to_specs[product_id]
            product_id_to_full_instance[product_id] = full_instance

        if not bucket_field:
            bucket_field = 'product_id'

        bucketed_results = OrderedDict()

        if ordering in self.DB_ORDERING_CHOICES:
            if ordering in self.PRICING_ORDERING_CHOICES:
                ordering_field = 'min_' + ordering
            else:
                ordering_field = ordering

            for entry in entities:
                product = product_id_to_full_instance[entry['product']]

                bucket = product.specs[bucket_field]

                if bucket not in bucketed_results:
                    bucketed_results[bucket] = OrderedDict()

                if product not in bucketed_results[bucket]:
                    bucketed_results[bucket][product] = {
                        'ordering_value': entry[ordering_field],
                        'prices': product_id_to_prices[product.id]
                    }
        else:
            # Ordering was based on ES
            ordering_field = re.match(r'-?(.+)$', ordering).groups()[0]

            if ordering_field == 'relevance':
                ordering_field = 'product_id'

            for es_product in es_results:
                product = product_id_to_full_instance[es_product['product_id']]
                bucket = product.specs[bucket_field]

                if bucket not in bucketed_results:
                    bucketed_results[bucket] = OrderedDict()

                bucketed_results[bucket][product] = {
                    'ordering_value': product.specs.get(ordering_field, None),
                    'prices': product_id_to_prices[product.id]
                }

        return bucketed_results

    def paginate_bucketed_results(self, request, bucketed_results):
        bucketed_results_list = list(bucketed_results.items())

        paginator = ProductsBrowsePagination()
        page = request.query_params.get(paginator.page_query_param, 1)
        try:
            page = int(page)
        except ValueError:
            page = 1

        page_size = paginator.get_page_size(request)

        offset = (page - 1) * page_size
        upper_bound = page * page_size

        return bucketed_results_list[offset:upper_bound]

    def serialize_results(self, request, bucketed_results_page):
        bucketed_results_page_for_serialization = []
        for bucket, products_dict in bucketed_results_page:
            product_entries = []
            for product, product_data in products_dict.items():
                product_entries.append({
                    'product': product,
                    'prices': product_data['prices'],
                    'ordering_value': product_data['ordering_value'],
                })
            bucketed_results_page_for_serialization.append({
                'bucket': bucket,
                'product_entries': product_entries
            })

        return CategoryBrowseResultSerializer(
            bucketed_results_page_for_serialization, many=True,
            context={'request': request}
        )
