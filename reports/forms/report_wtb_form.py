import io
from collections import defaultdict

import xlsxwriter
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Min
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user

from category_columns.models import CategoryColumn
from wtb.models import WtbBrand, WtbEntity
from solotodo.models import Category, Store, Entity, Country, StoreType, \
    Currency, EsProduct
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportWtbForm(forms.Form):
    wtb_brand = forms.ModelChoiceField(
        queryset=WtbBrand.objects.all())
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False)
    stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all(),
        required=False)
    countries = forms.ModelMultipleChoiceField(
        queryset=Country.objects.all(),
        required=False)
    store_types = forms.ModelMultipleChoiceField(
        queryset=StoreType.objects.all(),
        required=False)
    currency = forms.ModelChoiceField(
        queryset=Currency.objects.all(),
        required=False)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        valid_categories = get_objects_for_user(user, 'view_category_reports',
                                                Category)
        self.fields['categories'].queryset = valid_categories

        valid_stores = get_objects_for_user(user, 'view_store_reports', Store)
        self.fields['stores'].queryset = valid_stores

    def clean_stores(self):
        selected_stores = self.cleaned_data['stores']
        if selected_stores:
            return selected_stores
        else:
            return self.fields['stores'].queryset

    def clean_categories(self):
        selected_categories = self.cleaned_data['categories']
        if selected_categories:
            return selected_categories
        else:
            return self.fields['categories'].queryset

    def generate_report(self):
        wtb_brand = self.cleaned_data['wtb_brand']
        categories = self.cleaned_data['categories']
        stores = self.cleaned_data['stores']
        countries = self.cleaned_data['countries']
        store_types = self.cleaned_data['store_types']
        currency = self.cleaned_data['currency']

        brand = wtb_brand.brand
        product_to_wtb_entity_dict = defaultdict(lambda: [])

        wtb_entities = WtbEntity.objects.filter(brand=wtb_brand,
                                                category__in=categories,
                                                product__isnull=False)

        for wtb_entity in wtb_entities:
            product_to_wtb_entity_dict[wtb_entity.product_id]\
                .append(wtb_entity)

        es = Entity.objects.filter(product__brand=brand, store__in=stores)\
            .get_available()\
            .select_related(
            'product__instance_model',
            'cell_plan__instance_model',
            'active_registry',
            'currency',
            'store__country',
            'category')\
            .order_by('product')

        if countries:
            es = es.filter(store__country__in=countries)

        if store_types:
            es = es.filter(store__type__in=store_types)

        product_ids = [p['product_id'] for p in es.order_by('product_id')
                       .values('product_id').distinct()]

        es_search = EsProduct.search().filter('terms', product_id=product_ids)
        es_dict = {e.product_id: e.to_dict()
                   for e in es_search.scan()}

        output = io.BytesIO()

        # Create a workbook and add a worksheet
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})

        worksheet = workbook.add_worksheet()

        url_format = workbook.add_format({
            'font_color': 'blue',
            'font_size': 10
        })

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10
        })

        if len(categories) == 1:
            specs_columns = CategoryColumn.objects.filter(
                field__category=categories[0],
                purpose=settings.REPORTS_PURPOSE_ID,
                is_extended=False
            )
        else:
            specs_columns = None

        cell_plans_in_entities = [e.cell_plan for e in
                                  es.filter(cell_plan__isnull=False)]

        headers = [
            'Identificador',
            'Nombre',
            'Producto'
        ]

        cell_plan_prices_dict = {}
        if cell_plans_in_entities:
            headers.append('Plan celular')
            headers.append('Precio plan celular')

            cell_plan_entities = Entity.objects.filter(
                product__in=cell_plans_in_entities).get_available().values(
                'product').annotate(
                min_price=Min('active_registry__normal_price'))

            cell_plan_prices_dict = {e['product']: e['min_price']
                                     for e in cell_plan_entities}

        headers.extend([
            'Tienda',
            'País',
            'SKU',
            'Condición',
            'Fecha muestra',
            'Moneda',
            'Precio normal',
            'Precio oferta'
        ])

        cell_monthly_payments_in_entities = es.filter(
            active_registry__cell_monthly_payment__isnull=False)

        if cell_monthly_payments_in_entities:
            if cell_plans_in_entities:
                headers.append('Cuota arriendo')

        if currency:
            headers.extend([
                'Precio normal ({})'.format(currency.iso_code),
                'Precio oferta ({})'.format(currency.iso_code),
            ])

        headers.append('Nombre en tienda')
        if specs_columns:
            headers.extend([column.field.label for column in specs_columns])
        else:
            headers.extend(['Categoría'])

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1

        for e in es:
            es_entry = es_dict[e.product_id]

            # Wtb
            product_wtb_entities = product_to_wtb_entity_dict.get(
                e.product_id, [None])

            for wtb_entity in product_wtb_entities:
                col = 0
                if wtb_entity:
                    worksheet.write(row, col, wtb_entity.key)

                    col += 1

                    worksheet.write_url(
                        row, col,
                        wtb_entity.url,
                        string=wtb_entity.name,
                        cell_format=url_format)

                    col += 1
                else:
                    worksheet.write(row, col, 'N/A')

                    col += 1

                    worksheet.write(row, col, 'N/A')

                    col += 1

                # Product

                worksheet.write_url(
                    row, col,
                    '{}products/{}'.format(
                        settings.PRICING_HOST, e.product.id),
                    string=str(e.product),
                    cell_format=url_format)

                col += 1

                # Cell plan

                if cell_plans_in_entities:
                    cell_plan = e.cell_plan
                    if cell_plan:
                        cell_plan_price = cell_plan_prices_dict.get(
                            cell_plan.id, 'N/A')

                        worksheet.write_url(
                            row, col,
                            '{}products/{}'.format(settings.PRICING_HOST,
                                                   cell_plan.id),
                            string=str(e.cell_plan),
                            cell_format=url_format)
                        worksheet.write(row, col + 1, cell_plan_price)
                    else:
                        worksheet.write(row, col, 'N/A')
                        worksheet.write(row, col + 1, 'N/A')

                    col += 2

                # Store

                worksheet.write(row, col, str(e.store))
                col += 1

                # Country

                worksheet.write(row, col, str(e.store.country))
                col += 1

                # SKU

                if e.sku:
                    sku_text = str(e.sku)
                else:
                    sku_text = 'N/A'

                worksheet.write_url(
                    row, col,
                    '{}skus/{}'.format(settings.PRICING_HOST, e.id),
                    string=sku_text,
                    cell_format=url_format)
                col += 1

                # Condition
                worksheet.write(row, col, str(e.condition_as_text))
                col += 1

                # Date

                worksheet.write(row, col, e.active_registry.timestamp.date(),
                                date_format)
                col += 1

                # Currency

                worksheet.write(row, col, str(e.currency.iso_code))
                col += 1

                # Normal price

                worksheet.write(row, col, e.active_registry.normal_price)
                col += 1

                # Offer price
                worksheet.write(row, col, e.active_registry.offer_price)
                col += 1

                # Cell monthly payment
                if cell_monthly_payments_in_entities:
                    if e.active_registry.cell_monthly_payment is not None:
                        cell_monthly_payment_text = \
                            e.active_registry.cell_monthly_payment
                    else:
                        cell_monthly_payment_text = 'No aplica'
                    worksheet.write(row, col, cell_monthly_payment_text)
                    col += 1

                # Converted prices
                if currency:
                    converted_normal_price = currency.convert_from(
                        e.active_registry.normal_price, e.currency)
                    worksheet.write(row, col, converted_normal_price)
                    col += 1

                    converted_offer_price = currency.convert_from(
                        e.active_registry.offer_price, e.currency)
                    worksheet.write(row, col, converted_offer_price)
                    col += 1

                # Store name
                worksheet.write(row, col, e.name)
                col += 1

                if specs_columns:
                    for column in specs_columns:
                        worksheet.write(row, col, es_entry['specs'].get(
                            column.field.es_field, 'N/A'))
                        col += 1
                else:
                    worksheet.write(row, col, str(e.category))

                row += 1

        worksheet.autofilter(0, 0, row - 1, len(headers) - 1)
        workbook.close()

        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()

        filename_template = 'wtb_report_%Y-%m-%d_%H:%M:%S'

        filename = timezone.now().strftime(filename_template)

        path = storage.save('reports/{}.xlsx'.format(filename),
                            file_for_upload)

        return {
            'file': file_value,
            'path': path
        }
