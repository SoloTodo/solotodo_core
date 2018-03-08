from collections import OrderedDict
from datetime import timedelta

import re
from django import forms
from django.db.models import Min, Q, Count, Case, When, IntegerField, F
from django.utils import timezone

from solotodo.filter_utils import IsoDateTimeRangeField
from solotodo.filters import ProductsBrowseEntityFilterSet
from solotodo.models import Country, Product, Currency
from solotodo.pagination import ProductsBrowsePagination
from solotodo.serializers import CategoryBrowseResultSerializer
from solotodo.utils import iterable_to_dict


class ProductsBrowseForm(forms.Form):
    PRICING_ORDERING_CHOICES = [
        'normal_price',
        'offer_price',
        'normal_price_usd',
        'offer_price_usd',
    ]
    DEFAULT_ORDERING = 'offer_price'

    DB_ORDERING_CHOICES = PRICING_ORDERING_CHOICES + ['leads']

    # If a start date is not given for the orderings that use it
    # (visits, leads), use the registries up to x days in the past
    DEFAULT_ORDERING_DATE_DAYS_DELTA = 3

    ordering = forms.CharField(required=False)
    ordering_country = forms.ModelChoiceField(
        queryset=Country.objects.all(),
        required=False
    )
    ordering_date = IsoDateTimeRangeField(required=False)

    search = forms.CharField(required=False)
    brand = forms.CharField(required=False)

    def get_products(self, request):
        if not self.is_valid():
            return self.errors

        # 1. Filtering and aggregation of entities
        entities = self.initial_entities(request).filter(
            product__isnull=False
        )

        # 2. Get the min, max, and 80th percentile normal and offer price
        price_ranges = self.entities_price_ranges(entities)

        ordering = self.ordering_or_default()

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

        brand = self.cleaned_data['brand']
        if brand:
            es_search = es_search.filter('term', brand_unicode=brand.lower())

        if search or brand:
            es_results = es_search[:len(product_ids)].execute()
            filtered_product_ids = [entry['product_id']
                                    for entry in es_results]
            entities = entities.filter(product__in=filtered_product_ids)
        else:
            es_results = es_search[:len(product_ids)].execute()

        # 6 - 7. Obtain price entries and bucket the results

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
        assert self.is_valid()

        # 1. Filtering and aggregation of entities
        entities = self.initial_entities(request).filter(
            product__instance_model__model__category=category
        )

        # 2. Get the min, max, and 80th percentile normal and offer price
        price_ranges = self.entities_price_ranges(entities)

        ordering = self.ordering_or_default()

        query_params = request.query_params.copy()

        # 3. DB ordering (if it applies)
        if ordering in self.DB_ORDERING_CHOICES:
            # The same parameters will be passed to the specs form, and there
            # the DB ordering choices are invalid, so pop them.
            query_params.pop('ordering', None)
            entities = self.order_entities_by_db(entities, ordering)

        # 4. Create ES search that filters and order based on technical terms
        # if ordering is passed. Also calculates the aggregation count for the
        # form filters

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

        # 5. Obtain filter aggs

        filter_aggs = specs_form.process_es_aggs(es_results.aggs)

        # 6 - 7. Obtain price entries and bucket the results

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

    def initial_entities(self, request):
        filterset = ProductsBrowseEntityFilterSet.create(request)

        # The default ordering below will
        # a. Be overriden (if the final ordering is based on the DB)
        # b. Act as a secondary ordering (if the first ordering is based on ES)

        return filterset.qs \
            .values('product', 'currency') \
            .annotate(
                min_normal_price=Min('active_registry__normal_price'),
                min_offer_price=Min('active_registry__offer_price'),
                min_normal_price_usd=Min(F('active_registry__normal_price') /
                                         F('currency__exchange_rate')),
                min_offer_price_usd=Min(F('active_registry__offer_price') /
                                        F('currency__exchange_rate'))
            ).order_by('min_offer_price_usd', 'product', 'currency')

    def order_entities_by_db(self, entities, ordering):
        if ordering in self.PRICING_ORDERING_CHOICES:
            ordering_field = 'min_' + ordering
            return entities.order_by(
                ordering_field, 'product', 'currency')
        elif ordering == 'leads':
            ordering_country = self.cleaned_data['ordering_country']
            ordering_date = self.cleaned_data['ordering_date']

            if ordering_date and ordering_date.start:
                start_timestamp = ordering_date.start
            else:
                start_timestamp = timezone.now() - timedelta(
                    days=self.DEFAULT_ORDERING_DATE_DAYS_DELTA)

            lead_filter = Q(
                entityhistory__lead__timestamp__gte=start_timestamp)

            if ordering_date and ordering_date.stop:
                lead_filter &= Q(
                    entityhistory__lead__timestamp__lte=ordering_date.stop)

            if ordering_country:
                lead_filter &= Q(store__country=ordering_country)

            return entities \
                .filter(lead_filter) \
                .annotate(leads=Count('entityhistory__lead')) \
                .order_by('-leads', 'product', 'currency')
        else:
            raise Exception('This condition is unreachable')

    def entities_price_ranges(self, entities):
        entities_count = entities.count()

        if not entities_count:
            return None

        price_ranges = {}
        for price_type in ['normal_price_usd', 'offer_price_usd']:
            price_field = 'min_' + price_type
            sorted_entities = entities.order_by(price_field)
            price_ranges[price_type] = {
                'min': sorted_entities.first()[price_field],
                'max': sorted_entities.last()[price_field],
                '80th': sorted_entities[int(entities_count * 0.8)][price_field]
            }

        return price_ranges

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
                    'ordering_value': product.specs[ordering_field],
                    'prices': product_id_to_prices[product.id]
                }

        return bucketed_results

    def ordering_or_default(self):
        ordering = self.cleaned_data['ordering']
        if not ordering:
            ordering = self.DEFAULT_ORDERING

        return ordering

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
