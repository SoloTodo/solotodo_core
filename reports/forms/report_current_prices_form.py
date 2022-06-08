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
    Entity, Product, EsProduct
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
    normal_price_usd_min = forms.DecimalField(
        required=False)
    normal_price_usd_max = forms.DecimalField(
        required=False)
    filename = forms.CharField(
        required=False)
    extended = forms.BooleanField(
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
        normal_price_usd_min = self.cleaned_data['normal_price_usd_min']
        normal_price_usd_max = self.cleaned_data['normal_price_usd_max']

        specs_products = [e.product_id
                          for e in es_product_search[:100000].execute()]

        if products:
            product_ids = [product.id for product in products]
            specs_products = list(set(specs_products) & set(product_ids))

        entities = Entity.objects\
            .filter(product__isnull=False,
                    product__in=specs_products) \
            .filter(product__instance_model__model__category=category,
                    store__in=stores) \
            .get_available() \
            .select_related('product__instance_model',
                            'cell_plan__instance_model',
                            'active_registry',
                            'currency',
                            'store',
                            'bundle') \
            .order_by('product') \
            .annotate(normal_price_usd=F('active_registry__normal_price') /
                      F('currency__exchange_rate'))

        if countries:
            entities = entities.filter(store__country__in=countries)

        if store_types:
            entities = entities.filter(store__type__in=store_types)

        if normal_price_usd_min:
            entities = entities.filter(
                normal_price_usd__gte=normal_price_usd_min)

        if normal_price_usd_max:
            entities = entities.filter(
                normal_price_usd__lte=normal_price_usd_max)

        product_ids = [x['product'] for x in entities.values('product')]

        es_search = EsProduct.search().filter('terms', product_id=product_ids)
        es_dict = {e.product_id: e.to_dict()
                   for e in es_search.scan()}

        output = io.BytesIO()

        # Create a workbook and add a worksheet.
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        extended = self.cleaned_data['extended']
        self.generate_worksheet(workbook, category, currency, entities,
                                es_dict, extended)

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
    def generate_worksheet(workbook, category, currency, es, es_dict,
                           extended):
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

        if not extended:
            specs_columns = specs_columns.filter(is_extended=False)

        cell_plans_in_entities = {}

        for e in es.filter(cell_plan__isnull=False):
            if e.cell_plan_id not in cell_plans_in_entities:
                cell_plans_in_entities[e.cell_plan_id] = e.cell_plan

        headers = [
            'Producto',
            'Bundle',
        ]

        cell_plan_installments = {
            'Movistar': 18,
            'Entel': 18,
            'Claro': 12,
            'WOM': 18
        }

        cell_plan_prices_dict = {}
        if cell_plans_in_entities:
            headers.append('Plan celular')
            headers.append('Plan celular (base)')
            headers.append('Tipo plan')
            headers.append('Modalidad adquisición equipo')
            headers.append('Precio plan celular')

            cell_plan_entities = Entity.objects.filter(
                product__in=cell_plans_in_entities.keys())\
                .get_available().values(
                'product').annotate(
                min_price=Min('active_registry__normal_price'))

            cell_plan_prices_dict = {e['product']: e['min_price']
                                     for e in cell_plan_entities}

        headers.extend([
            'Tienda',
            'Seller',
            'SKU',
            'URL',
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
                headers.append('Número de cuotas')

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
            'Número reviews',
            'Puntaje promedio reviews',
            '¿Posee promotor virtual?',
        ])

        headers.extend([column.field.label for column in specs_columns])

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1
        for e in es:
            col = 0
            es_entry = es_dict[e.product_id]

            # Product
            worksheet.write(row, col, str(e.product))
            col += 1

            # Bundle
            if e.bundle:
                bundle_name = str(e.bundle)
            else:
                bundle_name = 'N/A'

            worksheet.write(row, col, bundle_name)
            col += 1

            # Cell plan

            if cell_plans_in_entities:
                cell_plan = cell_plans_in_entities.get(e.cell_plan_id)
                if cell_plan:
                    cell_plan_price = cell_plan_prices_dict.get(
                        cell_plan.id, 'N/A')

                    worksheet.write(
                        row, col, str(cell_plan))
                    worksheet.write(
                        row, col + 1, str(cell_plan.specs['base_name']))

                    if e.active_registry.cell_monthly_payment is None:
                        plan_type = 'Prepago'
                    elif cell_plan.specs['portability_exclusive']:
                        plan_type = 'Portabilidad'
                    else:
                        plan_type = 'Línea nueva'

                    worksheet.write(row, col + 2, plan_type)
                    worksheet.write(row, col + 3,
                                    cell_plan.specs['lease_unicode'])
                    worksheet.write(row, col + 4, cell_plan_price)
                else:
                    worksheet.write(row, col, 'N/A')
                    worksheet.write(row, col + 1, 'N/A')
                    worksheet.write(row, col + 2, 'N/A')
                    worksheet.write(row, col + 3, 'N/A')
                    worksheet.write(row, col + 4, 'N/A')

                col += 5

            # Store

            worksheet.write(row, col, str(e.store))
            col += 1

            # Seller

            seller_name = str(e.seller) if e.seller else 'N/A'
            worksheet.write(row, col, seller_name)
            col += 1

            # SKU

            if e.sku:
                sku_text = str(e.sku)
            else:
                sku_text = 'N/A'

            worksheet.write(
                row, col, sku_text)
            col += 1

            # URL
            worksheet.write(row, col, e.url)
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
                    worksheet.write(
                        row, col, e.active_registry.cell_monthly_payment)

                    # TODO: solucion parche. Hay que revisar con mas calma
                    if e.active_registry.cell_monthly_payment and e.cell_plan:
                        plan_brand = e.cell_plan.specs['brand_unicode']
                        installments = cell_plan_installments.get(
                            plan_brand, 'N/A')

                        worksheet.write(row, col+1, installments)
                    else:
                        worksheet.write(row, col + 1, 'No aplica')
                else:
                    worksheet.write(row, col, 'No aplica')
                    worksheet.write(row, col+1, 'No aplica')
                col += 2

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

            # Review score
            review_avg_score = e.review_avg_score \
                if e.review_avg_score is not None else 'N/A'
            worksheet.write(row, col, review_avg_score)
            col += 1

            # Has virtual assistant
            has_virtual_assistant = e.has_virtual_assistant \
                if e.has_virtual_assistant is not None else 'N/A'
            worksheet.write(row, col, has_virtual_assistant)
            col += 1

            for column in specs_columns:
                worksheet.write(
                    row, col,
                    es_entry['specs'].get(column.field.es_field, 'N/A'))
                col += 1

            row += 1

        worksheet.autofilter(0, 0, row - 1, len(headers) - 1)
