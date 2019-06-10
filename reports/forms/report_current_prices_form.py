import io

import xlsxwriter
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Min
from django.db.models import F
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user

from category_columns.models import CategoryColumn
from solotodo.models import Category, Store, Country, StoreType, Currency, \
    Entity, Product
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportCurrentPricesForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all())
    stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all(),
        required=False)
    products = forms.ModelMultipleChoiceField(
        queryset=Product.objects.all(),
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
    normal_price_usd_0 = forms.DecimalField(
        required=False)
    normal_price_usd_1 = forms.DecimalField(
        required=False)
    filename = forms.CharField(
        required=False)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        valid_categories = get_objects_for_user(user, 'view_category_reports',
                                                Category)
        self.fields['category'].queryset = valid_categories

        valid_stores = get_objects_for_user(user, 'view_store_reports', Store)
        self.fields['stores'].queryset = valid_stores

    def clean_stores(self):
        selected_stores = self.cleaned_data['stores']
        if selected_stores:
            return selected_stores
        else:
            return self.fields['stores'].queryset

    def generate_report(self, es_product_search):
        category = self.cleaned_data['category']
        stores = self.cleaned_data['stores']
        products = self.cleaned_data['products']
        countries = self.cleaned_data['countries']
        store_types = self.cleaned_data['store_types']
        currency = self.cleaned_data['currency']
        normal_price_usd_0 = self.cleaned_data['normal_price_usd_0']
        normal_price_usd_1 = self.cleaned_data['normal_price_usd_1']

        specs_products = [e.product_id
                          for e in es_product_search[:100000].execute()]

        if products:
            product_ids = [product.id for product in products]
            specs_products = list(set(specs_products) & set(product_ids))

        es = Entity.objects.filter(product__isnull=False,
                                   product__in=specs_products) \
            .filter(
            product__instance_model__model__category=category,
            store__in=stores) \
            .get_available() \
            .select_related(
            'product__instance_model',
            'cell_plan__instance_model',
            'active_registry',
            'currency',
            'store') \
            .order_by('product').annotate(
            normal_price_usd=F('active_registry__normal_price') /
            F('currency__exchange_rate'))

        if countries:
            es = es.filter(store__country__in=countries)

        if store_types:
            es = es.filter(store__type__in=store_types)

        if normal_price_usd_0:
            es = es.filter(normal_price_usd__gte=normal_price_usd_0)

        if normal_price_usd_1:
            es = es.filter(normal_price_usd__lte=normal_price_usd_1)

        product_ids = [x['product'] for x in es.values('product')]

        es_search = Product.es_search().filter('terms', product_id=product_ids)
        es_dict = {e.product_id: e.to_dict()
                   for e in es_search[:100000].execute()}

        output = io.BytesIO()

        # Create a workbook and add a worksheet.
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        self.generate_worksheet(workbook, category, currency, es, es_dict)

        workbook.close()

        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()

        filename_template = self.cleaned_data['filename']
        if not filename_template:
            filename_template = 'current_prices_%Y-%m-%d_%H:%M:%S'

        filename = timezone.now().strftime(filename_template)

        path = storage.save('reports/{}.xlsx'.format(filename),
                            file_for_upload)

        return {
            'file': file_value,
            'filename': filename,
            'path': path
        }

    @staticmethod
    def generate_worksheet(workbook, category, currency, es, es_dict):
        worksheet = workbook.add_worksheet()

        date_format = workbook.add_format({
            'num_format': 'yyyy-mm-dd'
        })

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10
        })

        specs_columns = CategoryColumn.objects.filter(
            field__category=category,
            purpose=settings.REPORTS_PURPOSE_ID
        )

        cell_plans_in_entities = [e.cell_plan for e in
                                  es.filter(cell_plan__isnull=False)]

        headers = [
            'Producto',
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

        headers.extend([
            'Nombre en tienda',
            'ID Flixmedia',
            'Número imágenes',
            'Número videos',
            'Número reviews'
        ])

        headers.extend([column.field.label for column in specs_columns])

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1
        for e in es:
            col = 0
            es_entry = es_dict[e.product_id]

            # Product
            worksheet.write(
                row, col, str(e.product))

            col += 1

            # Cell plan

            if cell_plans_in_entities:
                cell_plan = e.cell_plan
                if cell_plan:
                    cell_plan_price = cell_plan_prices_dict.get(
                        cell_plan.id, 'N/A')

                    worksheet.write(
                        row, col, str(e.cell_plan))
                    worksheet.write(row, col + 1, cell_plan_price)
                else:
                    worksheet.write(row, col, 'N/A')
                    worksheet.write(row, col + 1, 'N/A')

                col += 2

            # Store

            worksheet.write(row, col, str(e.store))
            col += 1

            # SKU

            if e.sku:
                sku_text = str(e.sku)
            else:
                sku_text = 'N/A'

            worksheet.write(
                row, col, sku_text)
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

            # Flixmedia ID
            worksheet.write(row, col, e.flixmedia_id or 'N/A')
            col += 1

            # Picture count
            pictures = e.picture_urls_as_list()
            picture_count = len(pictures) if pictures is not None else 'N/A'
            worksheet.write(row, col, picture_count)
            col += 1

            # Video count
            videos = e.video_urls_as_list()
            video_count = len(videos) if videos is not None else 'N/A'
            worksheet.write(row, col, video_count)
            col += 1

            # Review count
            review_count = e.review_count \
                if e.review_count is not None else 'N/A'
            worksheet.write(row, col, review_count)
            col += 1

            for column in specs_columns:
                worksheet.write(row, col, es_entry.get(column.field.es_field,
                                                       'N/A'))
                col += 1

            row += 1

        worksheet.autofilter(0, 0, row - 1, len(headers) - 1)
