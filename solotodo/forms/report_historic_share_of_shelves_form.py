import io
import xlsxwriter
from collections import defaultdict
from datetime import timedelta

from django import forms
from django.core.files.base import ContentFile
from django.db.models.functions import ExtractWeek, ExtractIsoYear
from django_filters.fields import IsoDateTimeRangeField
from guardian.shortcuts import get_objects_for_user

from solotodo.models import Store, Country, Entity, EntityHistory, EsProduct
from solotodo.forms.share_of_shelves_form import ShareOfShelvesForm
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportHistoricShareOfShelvesForm(forms.Form):
    timestamp = IsoDateTimeRangeField()
    bucketing_field = forms.CharField(
        required=True)
    stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all(),
        required=False)
    countries = forms.ModelMultipleChoiceField(
        queryset=Country.objects.all(),
        required=False)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        valid_stores = get_objects_for_user(user, 'view_store', Store)
        self.fields['stores'].queryset = valid_stores

    def clean_stores(self):
        selected_stores = self.cleaned_data['stores']
        if selected_stores:
            return selected_stores
        else:
            return self.fields['stores'].queryset

    def generate_report(self, category, request):
        from category_specs_forms.models import CategorySpecsFormFilter

        timestamp = self.cleaned_data['timestamp']
        bucketing_field = self.cleaned_data['bucketing_field']

        data = self.get_data(category, request.query_params)
        spec_filters = CategorySpecsFormFilter.objects.filter(
            filter__category=category,
            filter__name=bucketing_field)

        spec_filter = spec_filters[0]

        iter_date = timestamp.start
        one_week = timedelta(days=7)
        end_year, end_week = timestamp.stop.isocalendar()[:2]
        year_weeks = []

        while True:
            year, week = iter_date.isocalendar()[:2]
            year_weeks.append('{}-{}'.format(year, week))

            if year == end_year and week == end_week:
                break

            iter_date += one_week

        aggs = data['aggs']
        bucket_and_year_weeks = aggs.keys()
        bucketing_values = set()

        for bucket_and_year_week in bucket_and_year_weeks:
            bucketing_values.add(bucket_and_year_week[0])

        bucketing_values = list(bucketing_values)
        bucketing_values.sort()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)
        worksheet = workbook.add_worksheet()

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10
        })

        headers = [
            spec_filter.label
        ]

        for year_week in year_weeks:
            headers.append(year_week)

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1

        for bucketing_value in bucketing_values:
            col = 0
            worksheet.write(row, col, bucketing_value)
            col += 1
            for year_week in year_weeks:
                value = aggs.get((bucketing_value, year_week), 0)
                worksheet.write(row, col, value)
                col += 1
            row += 1

        workbook.close()

        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)
        storage = PrivateS3Boto3Storage()
        filename = "reports/historic_share_of_shelves.xlsx"
        path = storage.save(filename, file_for_upload)

        return {
            'file': file_value,
            'path': path
        }

    def get_data(self, category, query_params):
        stores = self.cleaned_data['stores']
        countries = self.cleaned_data['countries']
        timestamp = self.cleaned_data['timestamp']
        bucketing_field = self.cleaned_data['bucketing_field']

        ehs = EntityHistory.objects.filter(
            entity__product__isnull=False,
            entity__category=category,
            entity__store__in=stores,
            timestamp__gte=timestamp.start,
            timestamp__lte=timestamp.stop) \
            .get_available() \
            .annotate(week=ExtractWeek('timestamp'),
                      year=ExtractIsoYear('timestamp'))

        if countries:
            ehs = ehs.filter(entity__store__country__in=countries)

        entity_ids = [x['entity'] for x in
                      ehs.order_by('entity').values('entity').distinct()]

        entities = Entity.objects.filter(id__in=entity_ids)
        entity_dict = {e.id: e for e in entities}

        product_ids = [e['product'] for e in entities.order_by('product')
                       .values('product').distinct()]

        es_search = EsProduct.category_search(category).filter(
            'terms', product_id=product_ids)

        specs_form_class = category.specs_form()
        specs_form = specs_form_class(query_params)

        es_results = specs_form.get_es_products(
            es_search)[:len(product_ids)].execute()

        # Filter entity history with filtered products
        es_product_ids = [e.product_id for e in es_results]
        ehs = ehs.filter(entity__product__in=es_product_ids)
        ehs = ehs.order_by('entity', 'year', 'week') \
            .values('entity', 'year', 'week').distinct()

        # Create product dict
        es_dict = {e.product_id: e.to_dict()
                   for e in es_results}

        es_field = ShareOfShelvesForm.get_bucketing_es_field(
            category, bucketing_field)
        aggs = defaultdict(lambda: 0)

        for eh in ehs:
            entity = entity_dict[eh['entity']]
            product = es_dict[entity.product_id]
            bucketing_value = product['specs'][es_field]

            if isinstance(bucketing_value, bool):
                bucketing_value = 'Sí' if bucketing_value else 'No'

            if isinstance(bucketing_value, list):
                bucketing_value = ' / '.join(bucketing_value)

            product_bucket = (bucketing_value,
                              '{}-{}'.format(eh['year'], eh['week']))

            aggs[product_bucket] += 1

        return {
            'aggs': aggs,
        }
