from collections import OrderedDict
from datetime import timedelta

from django import forms
from django.db.models import Min, Q, Count, Case, When, IntegerField, F
from django.utils import timezone

from solotodo.filter_utils import IsoDateTimeRangeField
from solotodo.filters import CategoryBrowseEntityFilterSet
from solotodo.models import Country, Product, Currency
from solotodo.pagination import CategoryBrowsePagination
from solotodo.serializers import CategoryBrowserResultSerializer
from solotodo.utils import iterable_to_dict


class CategoryBrowseForm(forms.Form):
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

    def get_products(self, category, request):
        assert self.is_valid()

        # 1. Filtering and aggregation of entities
        filterset = CategoryBrowseEntityFilterSet.create(category, request)
        entities = filterset.qs \
            .values('product', 'currency') \
            .annotate(
                min_normal_price=Min('active_registry__offer_price'),
                min_offer_price=Min('active_registry__offer_price'),
                min_normal_price_usd=Min(F('active_registry__normal_price') /
                                         F('currency__exchange_rate')),
                min_offer_price_usd=Min(F('active_registry__offer_price') /
                                        F('currency__exchange_rate'))
            ) \
            .order_by('min_offer_price_usd', 'product', 'currency')

        # The default ordering above will
        # a. Be overriden (if the final ordering is based on the DB)
        # b. Act as a secondary ordering (if the first ordering is based on ES)

        ordering = self.cleaned_data['ordering']
        if not ordering:
            ordering = self.DEFAULT_ORDERING

        query_params = request.query_params.copy()

        # 2. DB ordering (if it applies)
        if ordering in self.DB_ORDERING_CHOICES:
            query_params.pop('ordering', None)

            if ordering in self.PRICING_ORDERING_CHOICES:
                ordering_field = 'min_' + ordering
                entities = entities.order_by(
                    ordering_field, 'product', 'currency')
            elif ordering == 'leads':
                ordering_country = self.cleaned_data['ordering_country']
                ordering_date = self.cleaned_data['ordering_date']

                start_timestamp = ordering_date.start
                if not start_timestamp:
                    start_timestamp = timezone.now() - timedelta(
                        days=self.DEFAULT_ORDERING_DATE_DAYS_DELTA)

                lead_filter = Q(
                    entityhistory__lead__timestamp__gte=start_timestamp)
                if ordering_date.stop:
                    lead_filter &= Q(
                        entityhistory__lead__timestamp__lte=ordering_date.stop)

                if ordering_country:
                    lead_filter &= Q(store__country=ordering_country)

                entities = entities\
                    .annotate(leads=Count(
                        Case(When(lead_filter, then=1),
                             output_field=IntegerField())))\
                    .order_by('-leads', 'product', 'currency')
            else:
                raise Exception('This condition is unreachable')

        # 3. Create ES search that filters and order based on technical terms
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

        # 4. Obtain filter aggs

        filter_aggs = specs_form.process_es_aggs(es_results.aggs)

        # 5. Generate price entries per product

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

        # 6. Bucket the results

        product_id_to_specs = {
            entry['_source']['product_id']: entry['_source']
            for entry in es_results.to_dict()['hits']['hits']
        }
        product_id_to_instance = iterable_to_dict(
            Product.objects.filter(pk__in=filtered_product_ids))
        product_id_to_full_instance = {}
        for product_id in filtered_product_ids:
            full_instance = product_id_to_instance[product_id]
            full_instance._specs = product_id_to_specs[product_id]
            product_id_to_full_instance[product_id] = full_instance

        bucket_field = specs_form.cleaned_data['bucket_field']
        if not bucket_field:
            bucket_field = 'id'

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
            for es_product in es_results:
                product = product_id_to_full_instance[es_product['product_id']]
                bucket = product.specs[bucket_field]

                if bucket not in bucketed_results:
                    bucketed_results[bucket] = OrderedDict()

                bucketed_results[bucket][product] = {
                    'ordering_value': product.specs[ordering],
                    'prices': product_id_to_prices[product.id]
                }

        # 7. Paginate

        bucketed_results_list = list(bucketed_results.items())

        paginator = CategoryBrowsePagination()
        page = request.query_params.get(paginator.page_query_param, 1)
        try:
            page = int(page)
        except ValueError:
            page = 1

        page_size = paginator.get_page_size(request)

        offset = (page - 1) * page_size
        upper_bound = page * page_size

        bucketed_results_page = bucketed_results_list[offset:upper_bound]

        # 8. Serialization

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

        serializer = CategoryBrowserResultSerializer(
            bucketed_results_page_for_serialization, many=True,
            context={'request': request}
        )

        return {
            'count': len(bucketed_results_list),
            'aggs': filter_aggs,
            'results': serializer.data
        }