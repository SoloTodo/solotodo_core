import io
from collections import OrderedDict

import xlsxwriter
from datetime import timedelta
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Min, Count
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user

from solotodo.models import Category, Store, Entity, Product
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportStoreAnalysisForm(forms.Form):
    store = forms.ModelChoiceField(
        queryset=Store.objects.all())
    competing_stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all(),
        required=False)
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False
    )
    price_type = forms.ChoiceField(
        choices=[
            ('normal_price', 'Normal price'),
            ('offer_price', 'Offer price'),
        ]
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        valid_categories = get_objects_for_user(user, 'view_category',
                                                Category)
        valid_stores = get_objects_for_user(user, 'view_stores',
                                            Store)

        self.base_fields['store'].queryset = valid_stores
        self.base_fields['competing_stores'].queryset = valid_stores
        self.base_fields['categories'].queryset = valid_categories

    def clean_competing_stores(self):
        selected_stores = self.cleaned_data['competing_stores']
        if selected_stores:
            return selected_stores
        else:
            return self.base_fields['competing_stores'].queryset

    def clean_categories(self):
        selected_categories = self.cleaned_data['categories']
        if selected_categories:
            return selected_categories
        else:
            return self.base_fields['categories'].queryset

    def generate_report(self):
        selected_store = self.cleaned_data['store']
        competing_stores = self.cleaned_data['competing_stores']
        categories = self.cleaned_data['categories']
        price_type = self.cleaned_data['price_type']

        all_stores = list(competing_stores)
        all_stores.append(selected_store)

        reference_date = timezone.now() - timedelta(days=7)

        es = Entity.objects.filter(product__isnull=False) \
            .filter(
            product__instance_model__model__category__in=categories,
            store__in=all_stores,
            active_registry__cell_monthly_payment__isnull=True
        ).get_available() \
            .select_related(
            'product__instance_model',
            'active_registry',
            'currency',
            'store') \
            .values('product', 'store') \
            .annotate(
            price=Min('active_registry__{}'.format(price_type)),
        ).order_by('price')

        product_ids = [e['product'] for e in es]

        products = Product.objects.filter(pk__in=product_ids).select_related(
            'instance_model__model__category')

        product_leads = Product.objects.filter(pk__in=product_ids) \
            .filter(
            entity__entityhistory__lead__timestamp__gte=reference_date,
        )\
            .annotate(
            leads=Count('entity__entityhistory__lead')
        ).order_by()

        products_leads_dict = {product.id: product.leads
                               for product in product_leads}
        products_dict = {product.id: product for product in products}

        store_ids = [e['store'] for e in es]
        stores_dict = {store.id: store for store in
                       Store.objects.filter(pk__in=store_ids)}

        data = OrderedDict()

        for entry in es:
            product = products_dict[entry['product']]

            if product not in data:
                data[product] = OrderedDict()

            store = stores_dict[entry['store']]
            data[product][store] = entry['price']

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

        headers = [
            'Estado',
            'Producto',
            'Categoría',
            'Leads',
            'Precio {}'.format(selected_store),
            'Competencia #1',
            'Precio competencia #1',
            'Competencia #2',
            'Precio competencia #2',
            'Competencia #3',
            'Precio competencia #3',
        ]

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1
        for product, stores_prices in data.items():
            price_in_selected_store = stores_prices.pop(selected_store, None)

            if price_in_selected_store:
                price_in_selected_store_text = price_in_selected_store

                if not stores_prices or \
                        list(stores_prices.values())[0] >= \
                        price_in_selected_store:
                    status = 'Precio óptimo'
                else:
                    status = 'Precio no óptimo'
            else:
                price_in_selected_store_text = 'No disponible'
                status = 'No disponible'

            col = 0

            # Status

            worksheet.write(row, col, status)
            col += 1

            # Product

            worksheet.write_url(
                row, col,
                '{}products/{}'.format(settings.BACKEND_HOST, product.id),
                string=str(product),
                cell_format=url_format)

            col += 1

            # Category

            worksheet.write_url(
                row, col,
                '{}categories/{}'.format(
                    settings.BACKEND_HOST,
                    product.category.id),
                string=str(product.category),
                cell_format=url_format)

            col += 1

            # Leads

            worksheet.write(row, col, products_leads_dict.get(product.id, 0))
            col += 1

            # Price in selected store

            worksheet.write(row, col, price_in_selected_store_text)
            col += 1

            # Price in competitors

            for competing_store, competing_price in \
                    list(stores_prices.items())[:3]:
                worksheet.write(row, col, str(competing_store))
                col += 1
                worksheet.write(row, col, competing_price)
                col += 1

            row += 1

        worksheet.autofilter(0, 0, row - 1, len(headers) - 1)

        workbook.close()

        output.seek(0)
        file_for_upload = ContentFile(output.getvalue())

        storage = PrivateS3Boto3Storage()
        path = storage.save('reports/store_analysis_{}.xlsx'.format(
            timezone.now().strftime('%Y-%m-%d_%H:%M:%S')),
            file_for_upload)

        return path
