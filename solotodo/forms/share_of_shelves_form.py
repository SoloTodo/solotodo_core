import io
import xlsxwriter

from django import forms
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError

from .products_browse_form import ProductsBrowseForm
from solotodo.models import Product, CategorySpecsFilter
from solotodo_core.s3utils import PrivateS3Boto3Storage
from reports.forms.report_current_prices_form import ReportCurrentPricesForm


class ShareOfShelvesForm(forms.Form):
    bucketing_field = forms.CharField(required=True)
    response_format = forms.CharField(required=False)

    def generate_xls(self, category, request):
        from category_specs_forms.models import CategorySpecsFormFilter

        data = self.get_data(category, request)
        results = data['results']

        bucketing_field = self.cleaned_data['bucketing_field']

        spec_filters = CategorySpecsFormFilter.objects.filter(
            filter__category=category,
            filter__name=bucketing_field)

        spec_filter = spec_filters[0]

        output = io.BytesIO()

        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)
        worksheet = workbook.add_worksheet()

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10
        })

        headers = [
            spec_filter.label,
            'Apariciones'
        ]

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1

        for result in results:
            col = 0
            worksheet.write(row, col, result['label'])

            col += 1
            worksheet.write(row, col, result['doc_count'])

            row += 1

        ReportCurrentPricesForm \
            .generate_worksheet(workbook, category, None,
                                data['entities'], data['es_dict'])

        workbook.close()

        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()

        filename = 'share_of_shelves.xlsx'

        path = storage.save(filename, file_for_upload)

        return {
            'file': file_value,
            'path': path
        }

    def generate_json(self, category, request):
        data = self.get_data(category, request)
        return {
            "aggs": data['aggs'],
            "results": data['results'],
            "price_ranges": data['price_ranges'],
        }

    def get_data(self, category, request):
        product_browse_form = ProductsBrowseForm(request.query_params)

        if not product_browse_form.is_valid():
            raise ValidationError(product_browse_form.errors)

        data = product_browse_form.get_category_entities(category, request)
        product_ids = [p['product']['id'] for p in data['results']]
        entities_agg = {}

        es_search = Product.es_search().filter('terms', product_id=product_ids)
        es_dict = {e.product_id: e.to_dict()
                   for e in es_search[:len(product_ids)].execute()}

        bucketing_field = self.cleaned_data['bucketing_field']

        spec_filters = CategorySpecsFilter.objects.filter(
            category=category,
            name=bucketing_field)

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

            if isinstance(key, list):
                key = ' / '.join(key)

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
            "price_ranges": data['price_ranges'],
            "entities": data['entities'],
            "es_dict": es_dict
        }
