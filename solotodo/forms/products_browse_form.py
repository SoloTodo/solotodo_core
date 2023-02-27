from collections import OrderedDict

from django import forms
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils.text import slugify

from rest_framework.reverse import reverse
from elasticsearch_dsl import A, Q

from solotodo.filters import CategoryFullBrowseEntityFilterSet
from solotodo.forms.product_specs_form import ProductSpecsForm
from solotodo.models import Product, Store, Category, \
    Brand, EsProduct
from solotodo.serializers import CategoryFullBrowseResultSerializer


class ProductsBrowseForm(forms.Form):
    stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all(),
        required=False
    )
    products = forms.ModelMultipleChoiceField(
        queryset=Product.objects.all(),
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
    exclude_marketplace = forms.BooleanField(required=False)
    exclude_without_part_number = forms.BooleanField(required=False)

    ordering = forms.CharField(required=False)
    search = forms.CharField(required=False)
    bucket_field = forms.CharField(required=False)

    page = forms.IntegerField(min_value=1, required=False)
    page_size = forms.IntegerField(min_value=1, max_value=200, required=False)

    ORDERING_CHOICES = {
        'offer_price_usd': {
            'script': "doc['offer_price_usd_with_coupon'].value",
            'direction': 'asc',
            'score_mode': 'min'
        },
        'normal_price_usd': {
            'script': "doc['normal_price_usd_with_coupon'].value",
            'direction': 'asc',
            'score_mode': 'min'
        },
        'price_per_unit': {
            'script': "doc['offer_price_usd_per_unit'].value",
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

    COLLAPSE_SIZE = 5

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(ProductsBrowseForm, self).__init__(*args, **kwargs)

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
        return original_bucket_field or 'specs.default_bucket'

    def clean_ordering(self):
        return self.cleaned_data['ordering'] or 'offer_price_usd'

    def clean_page(self):
        return self.cleaned_data['page'] or 1

    def clean_page_size(self):
        return self.cleaned_data['page_size'] or 10

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
                    es_field_name = '{}_price{}_with_coupon'.format(price_type, currency_choice)
                    price_filter &= Q('range', **{es_field_name: subquery_params})

        return price_filter

    def get_category_products(self, request, category=None):
        from solotodo.models import EsProduct, EsEntity

        assert self.is_valid()

        ordering = self.cleaned_data['ordering']

        if category:
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

            specs_form_class = category.specs_form()
            specs_form = specs_form_class(specs_form_query)
        else:
            specs_form = ProductSpecsForm(request.query_params)
            assert ordering in self.ORDERING_CHOICES

        assert specs_form.is_valid()

        store_ids = [x.id for x in self.cleaned_data['stores']]
        stores_filter = Q('terms', store_id=store_ids)
        price_filter = self.get_price_filter()

        if self.cleaned_data['exclude_refurbished']:
            condition_filter = Q(
                'term', condition='https://schema.org/NewCondition')
        else:
            condition_filter = Q()

        if self.cleaned_data['exclude_marketplace']:
            marketplace_filter = ~Q('exists', field='seller')
        else:
            marketplace_filter = Q()

        search = EsProduct.search()

        if category:
            search = search.filter('term', category_id=category.id)

        if self.cleaned_data['products']:
            search = search.filter(
                'terms', product_id=[x.id for x in
                                     self.cleaned_data['products']])

        if self.cleaned_data['db_brands']:
            search = search.filter(
                'terms', brand_id=[x.id for x in
                                   self.cleaned_data['db_brands']])

        if self.cleaned_data['exclude_without_part_number']:
            search = search.filter(Q('exists', field='part_number'))

        # Main part of the query. Returns the products:
        # * Filtered by store, refurbished status, price, markeplate status
        #   and specs
        # * Ordered by one of the available choices (offer_price_usd by def)
        # * Grouped ("collapsed") by the given bucket_key, or by product_id by
        #   default

        entities_filter = stores_filter & condition_filter & price_filter & \
            marketplace_filter
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
                                params.min_reference_price - params.min_price; 
                            """
                          )

            discount_per_product_dict = {
                x['key']: max(x['discount']['value'], 0) for x in
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
            sort_params = {'_score': 'desc'}
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
            if keyword_search_type == 'filter':
                keywords_query = Product.query_es_by_search_string(
                    keywords, mode='AND')
                search = search.filter(keywords_query)
            elif keyword_search_type == 'query':
                keywords_query = Product.query_es_by_search_string(
                    keywords, mode='OR')
                search = search.query(keywords_query)
            else:
                raise Exception('Invalid keyword_search_type')

        search = search.sort(sort_params)
        search = search.post_filter(all_specs_filter)

        # Second part of the query. Add the aggregations of the specs
        all_filtered_bucket, active_filters_buckets = \
            specs_form.get_aggregation_buckets()

        filtered_products_bucket = search.aggs.bucket(
            'all_filtered_products', all_filtered_bucket)
        for field_name, bucket in active_filters_buckets.items():
            search.aggs.bucket(field_name, bucket)

        # Third part of the query. Obtain the stats aggregation for the price
        # results
        search.aggs.bucket('entity_prices', 'children', type='entity')\
            .metric('offer_price_usd', 'stats', field='offer_price_usd_with_coupon')\
            .metric('normal_price_usd', 'stats', field='normal_price_usd_with_coupon')

        # Fifth part, add a bucket to obtain the number of results
        filtered_products_bucket.metric(
            'result_count', 'cardinality',
            field=self.cleaned_data['bucket_field']
        )

        # Collapse (group) the search results based on the given bucket field
        # or the default one
        search = search.update_from_dict({
            'collapse': {
                'field': self.cleaned_data['bucket_field'],
                'inner_hits': {
                    'name': 'inner_products',
                    'size': self.COLLAPSE_SIZE,
                    'sort': sort_params
                }
            }
        })

        # Pagination and execution
        page = self.cleaned_data['page']
        page_size = self.cleaned_data['page_size']
        offset = (page - 1) * page_size
        search_result = search[offset:offset + page_size].execute().to_dict()

        # Obtain the full pricing information of the search results
        search_result_product_ids = []
        for hit_1 in search_result['hits']['hits']:
            for hit_2 in hit_1['inner_hits']['inner_products']['hits']['hits']:
                search_result_product_ids.append(
                    hit_2['_source']['product_id'])

        prices_search = EsEntity.search() \
            .filter(entities_filter).filter(
            'terms', product_id=search_result_product_ids)

        prices_search.aggs \
            .bucket('per_product', 'terms', field='product_id',
                    size=self.COLLAPSE_SIZE * page_size) \
            .metric('normal_price_usd', 'min', field='normal_price_usd_with_coupon') \
            .metric('offer_price_usd', 'min', field='offer_price_usd_with_coupon') \
            .bucket('price_per_currency', 'terms', field='currency_id') \
            .metric('normal_price', 'min', field='normal_price_with_coupon') \
            .metric('offer_price', 'min', field='offer_price_with_coupon')

        price_results = prices_search[:0].execute().to_dict()

        # Assemble the serialized json
        product_prices_agg = price_results['aggregations']['per_product'][
            'buckets']
        result_count = search_result['aggregations'][
            'all_filtered_products'].pop('result_count')['value']
        product_metadata_dict = {}

        for product_price_bucket in product_prices_agg:
            product_pricing_metadata = {
                'normal_price_usd': str(product_price_bucket[
                                            'normal_price_usd']['value']),
                'offer_price_usd': str(product_price_bucket[
                                           'offer_price_usd']['value'])
            }
            prices_per_currency = []
            for currency_bucket in product_price_bucket[
                    'price_per_currency']['buckets']:
                prices_per_currency.append({
                    'currency': reverse('currency-detail',
                                        args=[currency_bucket['key']],
                                        request=request),
                    'normal_price':
                        str(currency_bucket['normal_price']['value']),
                    'offer_price':
                        str(currency_bucket['offer_price']['value'])
                })

            product_pricing_metadata['prices_per_currency'] = \
                prices_per_currency
            product_metadata_dict[product_price_bucket['key']] = \
                product_pricing_metadata

        collapsed_results = []
        for hit in search_result['hits']['hits']:
            product_entries = []
            for inner_hit in hit['inner_hits']['inner_products']['hits'][
                    'hits']:
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

                product_metadata = product_metadata_dict.get(
                    product['id'], None)

                product_entries.append({
                    'product': product,
                    'metadata': {
                        'score': inner_hit['_score'],
                        'prices_per_currency': product_metadata[
                            'prices_per_currency'],
                        'normal_price_usd': product_metadata[
                            'normal_price_usd'],
                        'offer_price_usd': product_metadata['offer_price_usd']
                    }
                })

            collapsed_entry = {
                'bucket': str(hit['fields'][self.cleaned_data[
                    'bucket_field']][0]),
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

        aggs = specs_form.flatten_es_aggs(search_result['aggregations'])

        result = {
            'count': result_count,
            'results': collapsed_results,
            'price_ranges': price_ranges,
            'aggs': aggs
        }

        return result

    def get_category_entities(self, category, request):
        """
        Returns the available entities of queried products
        """
        # TODO Conditions filter
        from category_columns.models import CategoryColumn

        assert self.is_valid()

        # 1. Filtering and annotation of entities
        entities = CategoryFullBrowseEntityFilterSet.get_entities(
            request, category)

        query_params = request.query_params.copy()
        query_params.pop('ordering', None)
        specs_form_class = category.specs_form()
        specs_form = specs_form_class(query_params)
        assert specs_form.is_valid()

        # 2. Create ES search that filters based on technical terms.
        # Also calculates the aggregation count for the form filters

        product_ids = [entry['product'] for entry in
                       entities.values('product').distinct()]
        search = EsProduct.category_search(category).filter(
            'terms', product_id=product_ids)

        if self.cleaned_data['products']:
            search = search.filter(
                'terms', product_id=[x.id for x in
                                     self.cleaned_data['products']])

        if self.cleaned_data['db_brands']:
            search = search.filter(
                'terms', brand_id=[x.id for x in
                                   self.cleaned_data['db_brands']])

        all_specs_filter = specs_form.get_filter()

        keywords = self.cleaned_data['search']
        if keywords:
            keywords_query = Q('fuzzy', keywords={'value': keywords}) | \
                             Q('fuzzy', name={'value': keywords})

            search = search.filter(keywords_query)
        search = search.post_filter(all_specs_filter)

        # Second part of the query. Add the aggregations of the specs
        all_filtered_bucket, active_filters_buckets = \
            specs_form.get_aggregation_buckets()
        search.aggs.bucket('all_filtered_products', all_filtered_bucket)
        for field_name, bucket in active_filters_buckets.items():
            search.aggs.bucket(field_name, bucket)

        results = search[:10000].execute().to_dict()
        filtered_product_ids = [x['_source']['product_id']
                                for x in results['hits']['hits']]
        entities = entities.filter(product__in=filtered_product_ids)

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

        aggs = specs_form.flatten_es_aggs(results['aggregations'])

        return {
            'aggs': aggs,
            'results': serialized_data,
            'price_ranges': price_ranges
        }
