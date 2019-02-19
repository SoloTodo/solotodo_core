import io
from collections import OrderedDict

import xlsxwriter
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Min
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user

from category_columns.models import CategoryColumn
from solotodo.models import Category, Store, Entity, Product
from solotodo_core.s3utils import PrivateS3Boto3Storage
from wtb.models import WtbEntity


class ReportSecPricesForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all())
    stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all(),
        required=False)
    filename = forms.CharField(
        required=False
    )

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

    def generate_report(self):
        category = self.cleaned_data['category']
        stores = self.cleaned_data['stores']

        es = Entity.objects.filter(product__isnull=False) \
            .filter(
            product__instance_model__model__category=category,
            store__in=stores) \
            .get_available().order_by('product', 'store').values(
            'product', 'store').annotate(price=Min(
                'active_registry__offer_price'))

        product_store_price_dict = {
            (e['product'], e['store']): e['price'] for e in es
        }

        wtb_es = WtbEntity.objects.filter(
            brand=settings.WTB_TOPTEN_CHILE_BRAND,
            category=category,
            product__isnull=False
        ).order_by('product')

        report_row_keys = [
            {
                'sec_name': e.name,
                'sec_code': e.key,
                'product_id': e.product_id
            } for e in wtb_es
        ]

        wtb_product_ids = [x['product'] for x in wtb_es.values('product')]

        pricing_product_ids = [x['product'] for x in es.values('product')]
        additional_product_ids = [x for x in pricing_product_ids
                                  if x not in wtb_product_ids]
        additional_product_ids = list(OrderedDict.fromkeys(
            additional_product_ids).keys())

        report_row_keys.extend([
            {
                'sec_name': 'N/A',
                'sec_code': 'N/A',
                'product_id': product_id
            } for product_id in additional_product_ids
        ])

        product_ids = wtb_product_ids + additional_product_ids

        es_search = Product.es_search().filter('terms', product_id=product_ids)
        es_dict = {e.product_id: e.to_dict()
                   for e in es_search[:100000].execute()}

        output = io.BytesIO()

        # Create a workbook and add a worksheet.
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)
        worksheet = workbook.add_worksheet()

        url_format = workbook.add_format({
            'font_color': 'blue',
            'font_size': 10
        })

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10
        })

        specs_columns = CategoryColumn.objects.filter(
            field__category=category,
            purpose=settings.REPORTS_PURPOSE_ID
        )

        headers = [
            'Nombre SEC',
            'Código SEC',
            'Producto SoloTodo',
            'ID Producto SoloTodo',
            '¿Está disponible?'
        ]

        headers.extend([column.field.label for column in specs_columns])
        headers.extend([store.name for store in stores])

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1
        for report_key in report_row_keys:
            col = 0
            es_product = es_dict[report_key['product_id']]

            # Nombre SEC

            worksheet.write(row, col, report_key['sec_name'])
            col += 1

            # Código SEC

            worksheet.write(row, col, report_key['sec_code'])
            col += 1

            # Producto SoloTodo

            worksheet.write_url(
                row, col,
                '{}products/{}'.format(settings.PRICING_HOST,
                                       es_product['product_id']),
                string=es_product['unicode'],
                cell_format=url_format)

            col += 1

            # ID Producto

            worksheet.write(row, col, es_product['product_id'])
            col += 1

            # Esta disponible?

            worksheet.write(row, col,
                            es_product['product_id'] in pricing_product_ids)
            col += 1

            # Specs

            for column in specs_columns:
                worksheet.write(row, col,
                                es_product.get(column.field.es_field, 'N/A'))
                col += 1

            for store in stores:
                price = product_store_price_dict.get(
                    (es_product['product_id'], store.id), 'N/A')
                worksheet.write(row, col, price)
                col += 1

            row += 1

        worksheet.autofilter(0, 0, row - 1, len(headers) - 1)

        workbook.close()

        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()

        filename_template = self.cleaned_data['filename']
        if not filename_template:
            filename_template = 'sec_prices_%Y-%m-%d_%H:%M:%S'

        filename = timezone.now().strftime(filename_template)

        path = storage.save('reports/{}.xlsx'.format(filename),
                            file_for_upload)

        return {
            'file': file_value,
            'path': path
        }
