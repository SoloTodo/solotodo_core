import io
from collections import OrderedDict

import xlsxwriter
from datetime import timedelta
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Count
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
    layout = forms.ChoiceField(
        choices=[
            ('layout_1', 'layout_1'),
            ('layout_2', 'layout_2'),
        ]
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        valid_categories = get_objects_for_user(user, 'view_category_reports',
                                                Category)
        valid_stores = get_objects_for_user(user, 'view_store_reports', Store)

        self.fields['store'].queryset = valid_stores
        self.fields['competing_stores'].queryset = valid_stores
        self.fields['categories'].queryset = valid_categories

    def clean_competing_stores(self):
        selected_stores = self.cleaned_data['competing_stores']
        if selected_stores:
            return selected_stores
        else:
            return self.fields['competing_stores'].queryset

    def clean_categories(self):
        selected_categories = self.cleaned_data['categories']
        if selected_categories:
            return selected_categories
        else:
            return self.fields['categories'].queryset

    def generate_report(self):
        selected_store = self.cleaned_data['store']
        competing_stores = self.cleaned_data['competing_stores']
        categories = self.cleaned_data['categories']
        price_type = self.cleaned_data['price_type']
        layout = self.cleaned_data['layout']

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
            'product__instance_model__model__category',
            'product__brand',
            'active_registry',
            'currency',
            'store'
        ).order_by('active_registry__{}'.format(price_type))

        product_ids = list(set([e.product_id for e in es]))

        product_leads = Product.objects.filter(pk__in=product_ids) \
            .filter(
            entity__entityhistory__lead__timestamp__gte=reference_date,
        ) \
            .annotate(
            leads=Count('entity__entityhistory__lead')
        ).order_by()

        products_leads_dict = {product.id: product.leads
                               for product in product_leads}

        data = OrderedDict()

        for entity in es:
            product = entity.product

            if product not in data:
                data[product] = OrderedDict()

            if entity.store in data[product]:
                continue

            data[product][entity.store] = entity

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
            'Marca',
            'ID {}'.format(selected_store),
            'Visitas en SoloTodo',
            'Precio en tienda',
            'Diferencia de precio',
        ]

        if layout == 'layout_1':
            headers.extend([
                '1a competencia',
                '2a competencia',
                '3a competencia'
            ])
        elif layout == 'layout_2':
            headers.extend([
                'Competencia #1',
                'Precio Competencia #1',
                'Competencia #2',
                'Precio Competencia #2',
                'Competencia #3',
                'Precio Competencia #3'
            ])

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1
        for product, stores_entities in data.items():
            entity_in_selected_store = stores_entities.pop(
                selected_store, None)

            if entity_in_selected_store:
                price_in_selected_store_text = getattr(
                    entity_in_selected_store.active_registry, price_type)

                if not stores_entities:
                    status = 'Precio óptimo'
                    price_difference = 'N/A'
                else:
                    entity_in_first_position = list(
                        stores_entities.values())[0]
                    price_in_first_position = getattr(
                        entity_in_first_position.active_registry, price_type)
                    price_difference = \
                        price_in_selected_store_text - price_in_first_position

                    if price_difference < 0:
                        status = 'Precio óptimo'
                    else:
                        status = 'Precio no óptimo'
            else:
                price_difference = 'N/A'
                price_in_selected_store_text = 'No disponible'
                status = 'No disponible'

            col = 0

            # Status

            worksheet.write(row, col, status)
            col += 1

            # Product

            worksheet.write_url(
                row, col,
                '{}products/{}'.format(settings.PRICING_HOST, product.id),
                string=str(product),
                cell_format=url_format)

            col += 1

            # Category

            worksheet.write_url(
                row, col,
                '{}categories/{}'.format(
                    settings.PRICING_HOST,
                    product.category.id),
                string=str(product.category),
                cell_format=url_format)

            col += 1

            # Brand

            worksheet.write(row, col, str(product.brand))
            col += 1

            # SKU

            if entity_in_selected_store:
                sku = entity_in_selected_store.sku
            else:
                sku = 'N/A'

            worksheet.write(row, col, sku)
            col += 1

            # Leads

            worksheet.write(row, col, products_leads_dict.get(product.id, 0))
            col += 1

            # Price in selected store

            worksheet.write(row, col, price_in_selected_store_text)
            col += 1

            # Diferencia de precio

            worksheet.write(row, col, price_difference)
            col += 1

            # Price in competitors

            for competing_store, competing_entity in \
                    list(stores_entities.items())[:3]:
                competitor_price = getattr(competing_entity.active_registry,
                                           price_type)

                if layout == 'layout_1':
                    competitor_string = '{} ({})'.format(
                        competing_store,
                        competitor_price
                    )

                    worksheet.write(row, col, competitor_string)
                    col += 1
                elif layout == 'layout_2':
                    worksheet.write(row, col, str(competing_store))
                    worksheet.write(row, col + 1, competitor_price)
                    col += 2

            row += 1

        worksheet.autofilter(0, 0, row - 1, len(headers) - 1)

        workbook.close()

        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()
        path = storage.save('reports/store_analysis_{}.xlsx'.format(
            timezone.now().strftime('%Y-%m-%d_%H:%M:%S')),
            file_for_upload)
        filename = timezone.now().strftime('store_analysis_%Y-%m-%d_%H:%M:%S')

        return {
            'file': file_value,
            'filename': filename,
            'path': path
        }
