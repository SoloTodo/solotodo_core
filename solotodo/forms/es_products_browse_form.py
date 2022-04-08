import json
from collections import OrderedDict

from django import forms
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils.text import slugify

from rest_framework.reverse import reverse
from elasticsearch_dsl import A, Q

from solotodo.filters import CategoryFullBrowseEntityFilterSet
from solotodo.models import Country, Product, Entity, Store, Category, \
    Brand, EsProduct
from solotodo.pagination import ProductsBrowsePagination
from solotodo.serializers import CategoryFullBrowseResultSerializer


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
    normal_price_min = forms.DecimalField(required=False)
    normal_price_max = forms.DecimalField(required=False)
    offer_price_min = forms.DecimalField(required=False)
    offer_price_max = forms.DecimalField(required=False)
    normal_price_usd_min = forms.DecimalField(required=False)
    normal_price_usd_max = forms.DecimalField(required=False)
    offer_price_usd_min = forms.DecimalField(required=False)
    offer_price_usd_max = forms.DecimalField(required=False)

    exclude_refurbished = forms.BooleanField(required=False)

    ordering = forms.CharField(required=False)
    search = forms.CharField(required=False)
    bucket_field = forms.CharField(required=False)

    page = forms.IntegerField(min_value=1, required=False)
    page_size = forms.IntegerField(min_value=1, max_value=200, required=False)

    ORDERING_CHOICES = {
        'offer_price_usd': {
            'script': "doc['offer_price_usd'].value",
            'direction': 'asc',
            'score_mode': 'min'
        },
        'normal_price_usd': {
            'script': "doc['normal_price_usd'].value",
            'direction': 'asc',
            'score_mode': 'min'
        },
        'leads': {
            'script': "doc['leads'].value",
            'direction': 'desc',
            'score_mode': 'sum'
        },
        # Discount and relevance are special cases that have their
        # parameters hardcoded
        'discount': {},
        'relevance': {}
    }

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(EsProductsBrowseForm, self).__init__(*args, **kwargs)

    def clean_stores(self):
        requested_stores = self.cleaned_data['stores']

        if not requested_stores:
            return Store.objects.filter_by_user_perms(self.user, 'view_store')

        def _get_invalid_stores(reload_cache=False):
            valid_stores = requested_stores.filter_by_user_perms(
                self.user, 'view_store', reload_cache=reload_cache)
            return requested_stores.difference(valid_stores)

        invalid_stores = _get_invalid_stores()

        if invalid_stores:
            # Try flushing the cache
            invalid_stores = _get_invalid_stores(reload_cache=True)

            if invalid_stores:
                raise forms.ValidationError('Invalid stores: {}'.format(
                    [x.id for x in invalid_stores]))

        return requested_stores

    def clean_categories(self):
        requested_categories = self.cleaned_data['categories']

        if not requested_categories:
            return Category.objects.filter_by_user_perms(
                self.user, 'view_category')

        def _get_invalid_categories(reload_cache=False):
            valid_categories = requested_categories.filter_by_user_perms(
                self.user, 'view_category', reload_cache=reload_cache)
            return requested_categories.difference(valid_categories)

        invalid_categories = _get_invalid_categories()

        if invalid_categories:
            # Try flushing the cache
            invalid_categories = _get_invalid_categories(reload_cache=True)

            if invalid_categories:
                raise forms.ValidationError('Invalid categories: {}'.format(
                    [x.id for x in invalid_categories]))

        return requested_categories

    def clean_bucket_field(self):
        original_bucket_field = self.cleaned_data['bucket_field']
        return original_bucket_field or 'product_id'

    def clean_ordering(self):
        return self.cleaned_data['ordering'] or 'offer_price_usd'

    def clean_page(self):
        return self.cleaned_data['page'] or 1

    def clean_page_size(self):
        return self.cleaned_data['page_size'] or 10

    def clean_search(self):
        return self.cleaned_data['search'] or ''

    def get_price_filter(self):
        # Returns the ES DSL Query object that represents the entity-level
        # filter of the form price parameters
        price_filter = Q()

        for price_type in ['normal', 'offer']:
            for currency_choice in ['', '_usd']:
                subquery_params = {}

                for filter_type in ['min', 'max']:
                    form_field = '{}_price{}_{}'.format(price_type, currency_choice, filter_type)
                    form_field_value = self.cleaned_data[form_field]

                    if form_field_value is None:
                        continue

                    es_range_field_field = 'gte' if filter_type == 'min' else 'lte'
                    subquery_params[es_range_field_field] = form_field_value

                if subquery_params:
                    es_field_name = '{}_price{}'.format(price_type, currency_choice)
                    price_filter &= Q('range', **{es_field_name: subquery_params})

        return price_filter

    def get_category_products(self, category, request):
        from solotodo.models import EsProduct, EsEntity

        assert self.is_valid()

        ordering = self.cleaned_data['ordering']

        # Create the sub form for the category-dependant specs
        specs_form_query = request.query_params.copy()
        # Determine whether we or the specs form will handle the sorting
        if ordering in self.ORDERING_CHOICES:
            # We will handle the sorting, remove the field from the specs
            # params, otherwise it will be detected as invalid
            specs_form_query.pop('ordering', None)
        else:
            # The specs form will handle the sorting, so set ours to None
            ordering = None

        specs_form_class = category.specs_form(form_type='es')
        specs_form = specs_form_class(specs_form_query)

        assert specs_form.is_valid()

        store_ids = [x.id for x in self.cleaned_data['stores']]
        stores_filter = Q('terms', store_id=store_ids)
        price_filter = self.get_price_filter()

        if self.cleaned_data['exclude_refurbished']:
            condition_filter = Q('term', condition='https://schema.org/NewCondition')
        else:
            condition_filter = Q()

        search = EsProduct.search().filter('term', category_id=category.id)

        # Main part of the query. Returns the products:
        # * Filtered by store, refurbished status, price and specs
        # * Ordered by one of the available choices (offer_price_usd by def)
        # * Grouped ("collapsed") by the given bucket_key, or by product_id by
        #   default

        search = search.update_from_dict({
            'collapse': {
                'field': self.cleaned_data['bucket_field'],
                'inner_hits': {
                    'name': 'inner_products',
                    'size': 5
                }
            }
        })

        entities_filter = stores_filter & condition_filter & price_filter
        all_specs_filter = specs_form.get_filter()

        if ordering == 'discount':
            # Create a second search to determine the discount of each product.
            # As far as I know we can't do this calculation inside the main
            # query because it uses aggregations that can't be associated
            # with a particular product directly.

            discounts_search = EsEntity.search()\
                .filter(entities_filter)\
                .filter('has_parent', parent_type='product',
                        query=all_specs_filter)

            discounts_search.aggs\
                .bucket('products', 'terms', field='product_id', size=10000)\
                .metric('min_price', 'min', field='offer_price_usd')\
                .metric('min_reference_price', 'min',
                        field='reference_offer_price_usd')\
                .pipeline('discount', 'bucket_script',
                          buckets_path={
                              'min_price': 'min_price',
                              'min_reference_price': 'min_reference_price'
                          },
                          script="""
                            if (params.min_reference_price > 0) 
                                params.min_price / params.min_reference_price; 
                            else 
                                1;
                            """
                          )

            discount_per_product_dict = {
                x['key']: x['discount']['value'] for x in
                discounts_search[:0].execute().aggs.products.buckets
            }

            search = search.query(
                Q('script_score',
                  query=Q(),
                  script={
                      'params': discount_per_product_dict,
                      'source': """
                  if (params.containsKey(doc['product_id'].value.toString())) 
                      params.get(doc['product_id'].value.toString()); 
                  else 
                      0;
                  """
                  }))
            search = search.filter('has_child', type='entity',
                                   query=entities_filter)
            sort_params = {'_score': 'asc'}
            keyword_search_type = 'filter'
        elif ordering == 'relevance':
            search = search.filter('has_child', type='entity',
                                   query=entities_filter)
            keyword_search_type = 'query'
            sort_params = {'_score': 'desc'}
        elif ordering:
            ordering_metadata = self.ORDERING_CHOICES[ordering]
            script_score = ordering_metadata['script']

            # Create a query that gives the filtered entities a score
            # depending on our ordering choice. The filter query itself must be
            # a bool with an empty "must" field because otherwise ElasticSearch
            # won't even try and give it a score. Also the filters cannot be
            # in the "must" field because in that case they alter the
            # numeric value of the score, I don't know why.
            query = Q('function_score',
                      script_score={'script': script_score},
                      query=Q('bool', filter=entities_filter, must=Q()))
            search = search.query('has_child', type='entity', query=query,
                                  score_mode=ordering_metadata['score_mode'])

            sort_params = {'_score': ordering_metadata['direction']}
            keyword_search_type = 'filter'
        else:
            sort_params = specs_form.get_ordering()
            assert sort_params
            search = search.filter('has_child', type='entity',
                                   query=entities_filter)
            keyword_search_type = 'filter'

        keywords = self.cleaned_data['search']
        if keywords:
            keywords_query = Q(
                'multi_match',
                query=keywords,
                fields=['name', 'keywords']
            )

            if keyword_search_type == 'filter':
                search = search.filter(keywords_query)
            elif keyword_search_type == 'query':
                search = search.query(keywords_query)
            else:
                raise Exception('Invalid keyword_search_type')

        search = search.sort(sort_params)
        search = search.post_filter(all_specs_filter)

        # Second part of the query. Add the aggregations of the specs
        all_filtered_bucket, active_filters_buckets = specs_form.get_aggregation_buckets()

        filtered_products_bucket = search.aggs.bucket('all_filtered_products', all_filtered_bucket)
        for field_name, bucket in active_filters_buckets.items():
            search.aggs.bucket(field_name, bucket)

        # Third part of the query. Obtain the stats aggregation for the price
        # results
        search.aggs.bucket('entity_prices', 'children', type='entity')\
            .metric('offer_price_usd', 'stats', field='offer_price_usd')\
            .metric('normal_price_usd', 'stats', field='normal_price_usd')

        # Fourth part of the query. Obtain the best price for each product
        filtered_products_bucket\
            .bucket('price_per_product', 'terms', field='product_id',
                    size=10000)\
            .bucket('product_entities', 'children', type='entity')\
            .bucket('filtered_entities', 'filter', filter=entities_filter)\
            .metric('offer_price_usd', 'stats', field='offer_price_usd')\
            .metric('normal_price_usd', 'stats', field='normal_price_usd')

        # Pagination and execution
        page = self.cleaned_data['page']
        page_size = self.cleaned_data['page_size']
        offset = (page - 1) * page_size
        search_result = search[offset:offset + page_size].execute().to_dict()

        # Assemble the serialized json
        product_prices_agg = search_result['aggregations'][
            'all_filtered_products'].pop('price_per_product')['buckets']
        product_prices_dict = {
            bucket['key']: (
                bucket['product_entities']['filtered_entities']['normal_price_usd']['min'],
                bucket['product_entities']['filtered_entities']['offer_price_usd']['min']
            ) for bucket in product_prices_agg
        }

        collapsed_results = []
        for hit in search_result['hits']['hits']:
            product_entries = []
            for inner_hit in hit['inner_hits']['inner_products']['hits']['hits']:
                product = inner_hit['_source']
                product['id'] = product.pop('product_id')
                product['url'] = reverse('product-detail',
                                         args=[product['id']],
                                         request=request)
                product['category'] = reverse('category-detail',
                                              args=[product['category_id']],
                                              request=request)
                product['slug'] = slugify(product['name'])
                picture_path = product['specs'].get('picture', None)

                if picture_path:
                    picture_url = default_storage.url(picture_path)
                else:
                    picture_url = None

                product['picture_url'] = picture_url

                for key in ['category_id', 'category_name',
                            'product_relationships']:
                    del product[key]

                prices = product_prices_dict.get(product['id'], (None, None))

                product_entries.append({
                    'product': product,
                    'metadata': {
                        'score': inner_hit['_score'],
                        'normal_price_usd': prices[0],
                        'offer_price_usd': prices[1],
                    }
                })

            collapsed_entry = {
                'bucket': str(hit['fields'][self.cleaned_data['bucket_field']][0]),
                'product_entries': product_entries
            }
            collapsed_results.append(collapsed_entry)

        price_ranges_agg = search_result['aggregations']['entity_prices']
        price_ranges = {}
        for price_type in ['normal_price_usd', 'offer_price_usd']:
            price_range = price_ranges_agg[price_type]
            price_ranges[price_type] = {
                'min': price_range['min'],
                'max': price_range['max'],
                # "80th" is a legacy field, please remove once the
                # frontend no longer uses it
                '80th': price_range['avg'],
                'avg': price_range['avg']
            }

        aggs = {}
        aggregations = search_result['aggregations']
        for spec_field_name in specs_form.get_field_names():
            if spec_field_name in aggregations:
                agg_data = aggregations[spec_field_name]['terms']['buckets']
            else:
                agg_data = aggregations['all_filtered_products'][spec_field_name]['buckets']

            aggs[spec_field_name] = [{
                'id': x['key'],
                'doc_count': x['doc_count']
            } for x in agg_data]

        result = {
            'count': search_result['hits']['total']['value'],
            'results': collapsed_results,
            'price_ranges': price_ranges,
            'aggs': aggs
        }

        return result

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
        es_search = EsProduct.category_search(category).filter(
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
            purpose=settings.CATEGORY_PURPOSE_BROWSE_ID,
            is_extended=False
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
        from solotodo.models import EsProduct

        search = EsProduct.search()

        # Filter entities based on our form fields
        entities_filter = self.filter_entities()
        search = search.filter('has_child', type='entity',
                               query=entities_filter)

        ordering = self.cleaned_data['ordering'] or 'relevance'

        assert ordering in self.DB_ORDERING_CHOICES

        keywords = self.cleaned_data['search']
        pagination_params = self.pagination_params(request)

        if keywords:
            keywords_query = Product.query_es_by_search_string(keywords,
                                                               mode='OR')
            search = search.query(keywords_query)

        # Add the metrics to the query (prices, leads).
        product_stats_bucket = self.pricing_metrics(
            offset=pagination_params['offset'],
            page_size=pagination_params['page_size'],
        )
        search.aggs.bucket('entities', 'children', type='entity') \
            .bucket('filtered_entities', 'filter', filter=entities_filter) \
            .bucket('product_stats', product_stats_bucket)

        search.aggs.bucket('categories', 'terms', field='category_id', size=50)
        es_result = search[
                    pagination_params['offset']:
                    pagination_params['upper_bound']
                    ].execute().to_dict()
        aggregations = es_result['aggregations']
        metadata_per_product = OrderedDict()

        for e in aggregations['entities']['filtered_entities'][
                'product_stats']['buckets']:
            metadata_per_product[e['key']] = e

        if ordering == 'relevance':
            products = [e['_source'] for e in es_result['hits']['hits']]
        else:
            product_ids = list(metadata_per_product.keys())
            products_search = EsProduct.search()[:len(product_ids)].filter(
                'terms', product_id=product_ids)
            products_dict = {
                e['_source']['product_id']: e['_source'] for e in
                products_search.execute().to_dict()['hits']['hits']
            }
            products = [products_dict[key] for key in
                        metadata_per_product.keys()]

        # Assemble product entries with their prices, leads and discount
        products_metadata = self.calculate_product_metadata(
            aggregations['entities']['filtered_entities'][
                'product_stats']['buckets'],
            request
        )

        # Create the product_entries (product + metadata)
        products_metadata_dict = {x['product_id']: x
                                  for x in products_metadata}

        product_entries = []

        for product in products:
            product_entries.append({
                'product': self.serialize_product(product, request),
                'metadata': products_metadata_dict[product['id']]
            })

        # Category aggregations
        category_buckets = [
            {'id': x['key'], 'doc_count': x['doc_count']}
            for x in aggregations['categories']['buckets']
        ]

        return {
            'count': es_result['hits']['total']['value'],
            'metadata': {
                'category_buckets': category_buckets
            },
            'results': product_entries,
        }

    def filter_entities(self):
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
                entity_filter = {es_field: [x.id for x in
                                            self.cleaned_data[field_name]]}
                entities_filter &= Q('terms', **entity_filter)

        range_fields = ['normal_price', 'offer_price',
                        'normal_price_usd', 'offer_price_usd']

        for range_field in range_fields:
            start_value = self.cleaned_data[range_field + '_min']
            end_value = self.cleaned_data[range_field + '_max']

            range_params = {}

            if start_value:
                range_params['gte'] = start_value
            if end_value:
                range_params['lte'] = end_value

            if range_params:
                entities_filter &= Q('range', **{range_field: range_params})

        if self.cleaned_data['exclude_refurbished']:
            entities_filter &= Q(
                'term', condition='https://schema.org/NewCondition')

        return entities_filter

    def order_entries_by_db(self, product_entries, ordering):
        if not ordering or ordering == 'relevance':
            return product_entries

        if ordering in self.PRICING_ORDERING_CHOICES:
            reverse_results = False
        else:
            # Discount, leads
            reverse_results = True

        return sorted(product_entries, key=lambda x: x['metadata'][ordering],
                      reverse=reverse_results)

    def pricing_metrics(self, offset=None, page_size=None):
        product_stats_bucket = A('terms', field='product_id', size=100000)
        product_prices_per_currency_bucket = A('terms', field='currency_id',
                                               size=10)
        for pricing_field in ['normal_price_usd', 'offer_price_usd',
                              'reference_normal_price_usd',
                              'reference_offer_price_usd']:
            product_stats_bucket.metric(pricing_field, 'min',
                                        field=pricing_field)

        product_stats_bucket.pipeline(
            'discount',
            'bucket_script',
            buckets_path={
                'reference_offer_price_usd': 'reference_offer_price_usd',
                'offer_price_usd': 'offer_price_usd'
            },
            script='params.reference_offer_price_usd - params.offer_price_usd'
        )

        ordering = self.cleaned_data['ordering'] or 'relevance'

        if ordering in self.DB_ORDERING_CHOICES and ordering != 'relevance':
            direction = 'asc' if ordering in self.PRICING_ORDERING_CHOICES \
                else 'desc'

            kwargs = {
                'sort': [{
                    ordering: {'order': direction}
                }]
            }

            if offset is not None and page_size is not None:
                kwargs.update({
                    'from': offset,
                    'size': page_size
                })

            product_stats_bucket.pipeline(
                'sorting',
                'bucket_sort',
                **kwargs
            )

        for pricing_field in ['normal_price', 'offer_price',
                              'normal_price_usd', 'offer_price_usd']:
            product_prices_per_currency_bucket.metric(pricing_field, 'min',
                                                      field=pricing_field)
        product_stats_bucket.metric('leads', 'sum', field='leads')
        product_stats_bucket.bucket('per_currency',
                                    product_prices_per_currency_bucket)

        return product_stats_bucket

    def calculate_product_metadata(self, buckets, request):
        products_metadata = []

        for metadata_entry in buckets:
            prices_per_currency = []
            for currency_bucket in metadata_entry['per_currency']['buckets']:
                prices_per_currency.append({
                    'currency': reverse('currency-detail',
                                        args=[currency_bucket['key']],
                                        request=request),
                    'normal_price': currency_bucket['normal_price'][
                        'value'],
                    'offer_price': currency_bucket['offer_price']['value'],
                    'normal_price_usd':
                        currency_bucket['normal_price_usd']['value'],
                    'offer_price_usd': currency_bucket['offer_price_usd'][
                        'value'],
                })

            products_metadata.append({
                'product_id': metadata_entry['key'],
                'normal_price_usd': metadata_entry['normal_price_usd'][
                    'value'],
                'offer_price_usd': metadata_entry['offer_price_usd'][
                    'value'],
                'leads': metadata_entry['leads']['value'],
                'relevance': metadata_entry.get(
                    'relevance', {}).get('value', 0),
                'discount': metadata_entry['discount']['value'],
                'prices_per_currency': prices_per_currency
            })

        return products_metadata

    def serialize_product(self, product, request):
        product['id'] = product['product_id']
        product['url'] = reverse('product-detail',
                                 args=[product['product_id']], request=request)
        product['category'] = reverse('category-detail',
                                      args=[product['category_id']],
                                      request=request)
        product['slug'] = slugify(product['name'])

        picture_path = product['specs'].get('picture')

        if picture_path:
            picture_url = default_storage.url(picture_path)
        else:
            picture_url = None

        product['picture_url'] = picture_url

        for key in ['product_id', 'category_id', 'category_name',
                    'product_relationships']:
            del product[key]

        return product

    def calculate_price_ranges(self, product_entries):
        if not product_entries:
            return None

        price_stats = {}

        for price_field in ['normal_price_usd', 'offer_price_usd']:
            prices = sorted([x['metadata'][price_field]
                             for x in product_entries])

            price_stats[price_field] = {
                'min': prices[0],
                'max': prices[-1],
                '80th': prices[int(len(prices) * 0.8)]
            }

        return price_stats

    def bucket_results(self, product_entries, bucket_field=None):
        bucketed_results_dict = OrderedDict()

        for product_entry in product_entries:
            if bucket_field:
                key = str(product_entry['product']['specs'][bucket_field])
            else:
                key = str(product_entry['product']['id'])
            if key not in bucketed_results_dict:
                bucketed_results_dict[key] = []

            bucketed_results_dict[key].append(product_entry)

        bucketed_results = []
        for key, bucket_product_entries in bucketed_results_dict.items():
            bucketed_results.append({
                'bucket': key,
                'product_entries': bucket_product_entries
            })

        return bucketed_results

    def pagination_params(self, request):
        paginator = ProductsBrowsePagination()
        page = request.query_params.get(paginator.page_query_param, 1)
        try:
            page = int(page)
        except ValueError:
            page = 1

        page_size = paginator.get_page_size(request)

        offset = (page - 1) * page_size
        upper_bound = page * page_size

        return {
            'page': page,
            'page_size': page_size,
            'offset': offset,
            'upper_bound': upper_bound
        }
