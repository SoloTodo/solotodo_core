import io
import xlsxwriter

from django import forms
from django.core.files.base import ContentFile
from django.db.models.functions import ExtractWeek, ExtractYear
from guardian.shortcuts import get_objects_for_user

from solotodo.models import Category, Store, Country, Entity, EntityHistory, \
    CategorySpecsFilter
from solotodo.filter_utils import IsoDateTimeRangeField
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportHistoricShareOfShelvesForm(forms.Form):
    timestamp = IsoDateTimeRangeField()
    bucketing_field = forms.CharField(
        required=True)
    category = forms.ModelChoiceField(
        queryset=Category.objects.all())
    stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all(),
        required=False)
    countries = forms.ModelMultipleChoiceField(
        queryset=Country.objects.all(),
        required=False)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        valid_stores = get_objects_for_user(user, 'view_store_reports', Store)
        self.fields['stores'].queryset = valid_stores

    def clean_stores(self):
        selected_stores = self.cleaned_data['stores']
        if selected_stores:
            return selected_stores
        else:
            return self.fields['stores'].queryset

    def clean_countries(self):
        selected_countries = self.cleaned_data['countries']
        if selected_countries:
            return selected_countries
        else:
            return self.fields['countries'].queryset

    def generate_report(self, request):
        from category_specs_forms.models import CategorySpecsFormFilter

        timestamp = self.cleaned_data['timestamp']
        category = self.cleaned_data['category']
        bucketing_field = self.cleaned_data['bucketing_field']

        data = self.get_data(request)
        spec_filters = CategorySpecsFormFilter.objects.filter(
            filter__category=category,
            filter__name=bucketing_field)

        spec_filter = spec_filters[0]

        start_year = timestamp.start.isocalendar()[0]
        start_week = timestamp.start.isocalendar()[1]
        end_year = timestamp.stop.isocalendar()[0]
        end_week = timestamp.stop.isocalendar()[1]

        dates = []
        for y in range(start_year, end_year+1):
            for w in range(start_week, end_week+1):
                dates.append(str(y)+'-'+str(w))

        aggs = data['aggs']
        aggs_keys = aggs.keys()
        fields = []

        for key in aggs_keys:
            fields.append(key[0])

        fields = list(set(fields))
        fields.sort()

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

        for date in dates:
            headers.append(date)

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1

        for field in fields:
            col = 0
            worksheet.write(row, col, field)
            col += 1
            for date in dates:
                if (field, date) in aggs:
                    value = aggs[(field, date)]
                else:
                    value = 0
                worksheet.write(row, col, value)
                col += 1
            row += 1

        workbook.close()
        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()

        filename = "historic_share_of_shelves.xlsx"

        path = storage.save(filename, file_for_upload)

        return {
            'file': file_value,
            'path': path
        }

    def get_data(self, request):
        category = self.cleaned_data['category']
        countries = self.cleaned_data['countries']
        timestamp = self.cleaned_data['timestamp']
        bucketing_field = self.cleaned_data['bucketing_field']

        query_params = request.query_params.copy()

        ehs = EntityHistory.objects.filter(
            entity__product__isnull=False,
            entity__category=category,
            timestamp__gte=timestamp.start,
            timestamp__lte=timestamp.stop) \
            .get_available() \
            .annotate(week=ExtractWeek('timestamp'),
                      year=ExtractYear('timestamp'))

        if countries:
            ehs = ehs.filter(entity__store__country__in=countries)

        entity_ids = [x['entity']
                      for x in ehs.order_by('entity').values('entity')]
        entities = Entity.objects.filter(id__in=entity_ids)
        entity_dict = {e.id: e for e in entities}

        product_ids = set(entry['product']
                          for entry in entities.values('product'))
        es_search = category.es_search().filter(
            'terms', product_id=list(product_ids))

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

        spec_filters = CategorySpecsFilter.objects.filter(
            category=category,
            name=bucketing_field)

        spec_filter = spec_filters[0]

        if spec_filter.meta_model.is_primitive():
            es_field = spec_filter.es_field
        else:
            es_field = spec_filter.es_field + '_unicode'

        aggs = {}

        for eh in ehs:
            entity = entity_dict[eh['entity']]
            product = es_dict[entity.product_id]
            product_bucket = (product[es_field],
                              str(eh['year']) + '-' + str(eh['week']))

            if product_bucket not in aggs:
                aggs[product_bucket] = 0

            aggs[product_bucket] += 1

        return {
            'aggs': aggs,
        }
