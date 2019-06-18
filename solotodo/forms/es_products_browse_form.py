from collections import OrderedDict

from django import forms
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils.text import slugify

from rest_framework.reverse import reverse
from elasticsearch_dsl import A, Q

from solotodo.filters import CategoryFullBrowseEntityFilterSet
from solotodo.models import Country, Product, CategorySpecsFilter, Entity, \
    Store, Category, Brand, EsProduct
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
    normal_price_0 = forms.DecimalField(required=False)
    normal_price_1 = forms.DecimalField(required=False)
    offer_price_0 = forms.DecimalField(required=False)
    offer_price_1 = forms.DecimalField(required=False)
    normal_price_usd_0 = forms.DecimalField(required=False)
    normal_price_usd_1 = forms.DecimalField(required=False)
    offer_price_usd_0 = forms.DecimalField(required=False)
    offer_price_usd_1 = forms.DecimalField(required=False)

    PRICING_ORDERING_CHOICES = [
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
        requested_stores = self.cleaned_data['stores']

        if not requested_stores:
            return Store.objects.filter_by_user_perms(self.user, 'view_store')

        valid_stores = requested_stores.filter_by_user_perms(self.user,
                                                             'view_store')
        invalid_stores = requested_stores.exclude(
            pk__in=[x.id for x in valid_stores])

        if not invalid_stores:
            return requested_stores

        raise forms.ValidationError('Invalid stores: {}'.format(
            [x.id for x in invalid_stores]))

    def clean_categories(self):
        requested_categories = self.cleaned_data['categories']

        if not requested_categories:
            return Category.objects.filter_by_user_perms(
                self.user, 'view_category')

        valid_categories = requested_categories.filter_by_user_perms(
            self.user, 'view_category')
        invalid_categories = requested_categories.exclude(
            pk__in=[x.id for x in valid_categories])

        if not invalid_categories:
            return requested_categories

        raise forms.ValidationError(
            'Invalid categories: {}'.format(
                [x.id for x in invalid_categories]))

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
        from solotodo.es_models import EsEntity, EsProduct

        search = EsEntity.search()

        # Filter entities based on our form fields
        entities_filter = self.filter_entities()
        search = search.filter(entities_filter)

        ordering = self.cleaned_data['ordering'] or 'offer_price_usd'

        assert ordering in self.DB_ORDERING_CHOICES

        keywords = self.cleaned_data['search']

        if keywords:
            keywords_query = Q('simple_query_string', fields=['keywords'],
                               default_operator='or', query=keywords)
            search = search.query('has_parent', parent_type='product',
                                  query=keywords_query)

        # Add the metrics to the query (prices, leads).
        product_stats_bucket = self.pricing_metrics()
        search.aggs\
            .bucket('product_stats', product_stats_bucket)
        search.aggs.pipeline('offer_price_usd', 'stats_bucket',
                             buckets_path='product_stats>offer_price_usd')

        # Obtain the results
        es_result = search.execute().to_dict()

        products_metadata = self.calculate_product_metadata(
            es_result['aggregations']['product_stats']['buckets'],
            request
        )
        count = len(products_metadata)
        is_ordering_leads_or_discount = ordering not in \
            self.PRICING_ORDERING_CHOICES
        products_metadata = sorted(products_metadata,
                                   key=lambda x: x[ordering],
                                   reverse=is_ordering_leads_or_discount)
        product_ids = [x['product_id'] for x in products_metadata]

        es_products_search = EsProduct.search()\
            .filter('terms', product_id=product_ids)

        es_products_search.aggs.bucket(
            'categories', 'terms', field='category_id', size=50)
        es_products_search.aggs.bucket(
            'brands', 'terms', field='brand_id', size=50)

        es_products = es_products_search[:len(product_ids)].execute().to_dict()

        es_products_dict = {x['_source']['product_id']: x['_source']
                            for x in es_products['hits']['hits']}

        pagination_params = self.pagination_params(request)
        products_metadata = products_metadata[
            pagination_params['offset']:
            pagination_params['upper_bound']
        ]

        product_entries = []
        for product_metadata in products_metadata:
            serialized_product = self.serialize_product(
                es_products_dict[product_metadata['product_id']], request)
            del product_metadata['product_id']

            product_entries.append({
                'product': serialized_product,
                'metadata': product_metadata
            })

        price_metadata = es_result['aggregations']['offer_price_usd']

        categories_metadata = [{
            'id': x['key'],
            'doc_count': x['doc_count']
        } for x in es_products['aggregations']['categories']['buckets']]

        brands_metadata = [{
            'id': x['key'],
            'doc_count': x['doc_count']
        } for x in es_products['aggregations']['brands']['buckets']]

        metadata = {
            'offer_price_usd_stats': {
                'min': price_metadata['min'],
                'max': price_metadata['max'],
                'avg': price_metadata['avg']
            },
            'category_buckets': categories_metadata,
            'brand_buckets': brands_metadata
        }

        return {
            'count': count,
            'results': product_entries,
            'metadata': metadata
        }

    def get_category_products(self, category, request):
        from solotodo.es_models import EsProduct

        assert self.is_valid()

        search = EsProduct.search().filter('term', category_id=category.id)

        # Filter entities based on our form fields
        entities_filter = self.filter_entities()
        search = search.filter('has_child', type='entity',
                               query=entities_filter)

        specs_query_params = request.query_params.copy()

        # Determine the ordering we will need to execute manually in Python
        if not self.cleaned_data['ordering']:
            # Default: Offer price USD
            db_ordering = 'offer_price_usd'
        elif self.cleaned_data['ordering'] in self.DB_ORDERING_CHOICES:
            # If the ordering is explicitly given and resolved in Python
            # remove it from the params that will be passed to the specs form
            # as the ordering value will be invalid in that form
            db_ordering = specs_query_params.pop('ordering')[0]
        else:
            # The ordering is assumed to be based on a tech spec. If it is
            # invalid the spec form will handle and raise it
            db_ordering = None

        # Post_filter, ordering and aggregations based on technical terms.
        # Post filter is necessary because the specs aggregations rely on
        # having all of the products. For example if we filter by "Acer"
        # notebooks we also want to have the aggregations for the other brands
        # for UI purposes
        # Also adds a bucket with the normally filtered products to be used
        # by the metrics aggregation below.
        specs_form_class = category.specs_form(form_type='es')
        specs_form = specs_form_class(specs_query_params)
        search = specs_form.get_es_products(search)

        # Add the metrics to the query (prices, leads)
        product_stats_bucket = self.pricing_metrics()
        search.aggs['filtered_products'] \
            .bucket('entities', 'children', type='entity') \
            .bucket('filtered_entities', 'filter', filter=entities_filter) \
            .bucket('product_stats', product_stats_bucket)

        # Obtain the results
        es_result = search[:10000].execute().to_dict()

        # Assemble product entries with their prices, leads and discount
        products_metadata = self.calculate_product_metadata(
            es_result['aggregations']['filtered_products']['entities'][
                'filtered_entities']['product_stats']['buckets'],
            request
        )

        # Create the product_entries (product + metadata)
        products_metadata_dict = {x['product_id']: x
                                  for x in products_metadata}

        products = [entry['_source'] for entry in es_result['hits']['hits']]
        product_entries = []

        for product in products:
            product_entries.append({
                'product': self.serialize_product(product, request),
                'metadata': products_metadata_dict[product['id']]
            })

        # Sort based on DB (if given)
        product_entries = self.order_entries_by_db(product_entries,
                                                   db_ordering)

        # Obtain the price ranges for the matchign products
        price_ranges = self.calculate_price_ranges(product_entries)

        # Bucket the results
        bucket_field = specs_form.cleaned_data['bucket_field']
        bucketed_results = self.bucket_results(product_entries, bucket_field)

        # Paginate
        pagination_params = self.pagination_params(request)
        bucketed_results_page = \
            bucketed_results[pagination_params['offset']:
                             pagination_params['upper_bound']]

        filter_aggs = specs_form.process_es_aggs(es_result['aggregations'])

        return {
            'count': len(bucketed_results),
            'aggs': filter_aggs,
            'results': bucketed_results_page,
            'price_ranges': price_ranges
        }

    def get_share_of_shelves(self, category, request):
        data = self.get_category_entities(category, request)
        product_ids = [p['product']['id'] for p in data['results']]
        entities_agg = {}

        es_search = EsProduct.search().filter('terms', product_id=product_ids)
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
            'aggs': data['aggs'],
            'results': result,
            'price_ranges': data['price_ranges']
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
            start_value = self.cleaned_data[range_field + '_0']
            end_value = self.cleaned_data[range_field + '_1']

            range_params = {}

            if start_value:
                range_params['gte'] = start_value
            if end_value:
                range_params['lte'] = end_value

            if range_params:
                entities_filter &= Q('range', **{range_field: range_params})

        return entities_filter

    def order_entries_by_db(self, product_entries, ordering):
        if not ordering:
            return product_entries

        if ordering in self.PRICING_ORDERING_CHOICES:
            reverse_results = False
        else:
            # Discount, leads
            reverse_results = True

        return sorted(product_entries, key=lambda x: x['metadata'][ordering],
                      reverse=reverse_results)

    def pricing_metrics(self):
        product_stats_bucket = A('terms', field='product_id', size=100000)
        product_prices_per_currency_bucket = A('terms', field='currency_id',
                                               size=10)
        for pricing_field in ['normal_price_usd', 'offer_price_usd',
                              'reference_normal_price_usd',
                              'reference_offer_price_usd']:
            product_stats_bucket.metric(pricing_field, 'min',
                                        field=pricing_field)
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

            current_price = metadata_entry['offer_price_usd']['value']
            reference_price = metadata_entry['reference_offer_price_usd'][
                'value']

            products_metadata.append({
                'product_id': metadata_entry['key'],
                'normal_price_usd': metadata_entry['normal_price_usd'][
                    'value'],
                'offer_price_usd': metadata_entry['offer_price_usd'][
                    'value'],
                'leads': metadata_entry['leads']['value'],
                'discount': reference_price - current_price,
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
                    'product_entity']:
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
        if bucket_field:
            bucket_field = 'specs.{}'.format(bucket_field)
        else:
            bucket_field = 'id'

        bucketed_results_dict = OrderedDict()

        for product_entry in product_entries:
            key = str(product_entry['product'][bucket_field])
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
