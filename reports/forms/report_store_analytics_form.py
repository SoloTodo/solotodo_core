import io

from django import forms
from django.core.files.base import ContentFile
from django.utils import timezone
from django_filters.fields import IsoDateTimeRangeField
from google.cloud import bigquery
from guardian.shortcuts import get_objects_for_user
import pandas as pd

from solotodo.models import Category, Entity, Product, Store
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportStoreAnalyticsForm(forms.Form):
    store = forms.ModelChoiceField(
        queryset=Store.objects.all())
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False
    )
    timestamp = IsoDateTimeRangeField()

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        valid_categories = get_objects_for_user(user, 'view_category_reports',
                                                Category)
        valid_stores = get_objects_for_user(user, 'view_store_reports', Store)

        self.fields['store'].queryset = valid_stores
        self.fields['categories'].queryset = valid_categories

    def clean_categories(self):
        selected_categories = self.cleaned_data['categories']
        if selected_categories:
            return selected_categories
        else:
            return self.fields['categories'].queryset

    def generate_report(self):
        selected_store = self.cleaned_data['store']
        categories = self.cleaned_data['categories']
        timestamp = self.cleaned_data['timestamp']

        start_date = timestamp.start.strftime('%Y%m%d')
        stop_date = timestamp.stop.strftime('%Y%m%d')
        category_ids = ','.join(str(i)
                                for i in list(set([c.id for c in categories])))
        retailer_case_count = f'CASE WHEN retailer_id = {selected_store.id} THEN 1 END'
        retailer_case_price = f'CASE WHEN retailer_id = {selected_store.id} THEN price END'
        query = f'''
            SELECT
                product_id,
                count(*) as total_clicks,
                count({retailer_case_count}) as retailer_clicks,
                round((count({retailer_case_count}) / count(*)), 4) as precentage_clicks,
                sum(price) as total_price_sum,
                sum({retailer_case_price}) as retailer_sum,
                round((sum({retailer_case_price}) / sum(price)), 4) as percentage_sum,
                round(sum(price) / count(*)) as average_price,
                round(sum({retailer_case_price}) / count({retailer_case_count})) as retailer_average_price,
                max(price) as max_price,
                max({retailer_case_price}) as retailer_max_price,
                min(price) as min_price,
                min({retailer_case_price}) as retailer_min_price,
            FROM
                (SELECT
                    (SELECT ep.value.int_value
                    FROM UNNEST(event_params) AS ep
                    WHERE ep.key = 'product_id') AS product_id,
                    (SELECT ep.value.int_value
                    FROM UNNEST(event_params) AS ep
                    WHERE ep.key = 'category_id') AS category_id,
                    (SELECT ep.value.int_value
                    FROM UNNEST(event_params) AS ep
                    WHERE ep.key = 'precio') AS price,
                    (SELECT ep.value.int_value
                    FROM UNNEST(event_params) AS ep
                    WHERE ep.key = 'retailer_id') AS retailer_id,
                    (SELECT ep.value.string_value
                    FROM UNNEST(event_params) AS ep
                    WHERE ep.key = 'condition') AS condition,
                FROM
                    `solotodo-207819.analytics_340597961.events*`
                WHERE
                    event_name = 'click'
                AND event_date >= '{start_date}'
                AND event_date <= '{stop_date}')
            WHERE category_id in ({category_ids})
            AND condition = 'https://schema.org/NewCondition'
            GROUP BY product_id
            HAVING retailer_clicks > 0;
        '''

        client = bigquery.Client()

        query_job = client.query(query)
        products_df = query_job.to_dataframe()

        products = Product.objects.filter(
            pk__in=products_df['product_id'].to_list()).select_related(
                'instance_model__model__category',
                'brand'
        )
        current_product_ids = list(set([p.id for p in products]))

        products_df = products_df[products_df['product_id'].isin(
            current_product_ids)]

        if products_df.size != 0:
            es = Entity.objects.filter(product__isnull=False) \
                .filter(
                product__instance_model__model__category__in=categories,
                store=selected_store,
                active_registry__cell_monthly_payment__isnull=True
            ).get_available().select_related(
                'product',
                'active_registry'
            )
            entity_dict = {}
            for e in es:
                entity_dict[e.product_id] = int(e.active_registry.offer_price)

            products_dict = {
                product.id: {'name': product.name, 'category': product.category.name,
                             'brand': product.brand.name} for product in products}

            products_df['product_name'] = products_df.apply(
                lambda x: products_dict[x.product_id]['name'], axis=1)
            products_df['product_brand'] = products_df.apply(
                lambda x: products_dict[x.product_id]['brand'], axis=1)
            products_df['product_category'] = products_df.apply(
                lambda x: products_dict[x.product_id]['category'], axis=1)
            products_df['entity_price'] = products_df.apply(
                lambda x: entity_dict.get(x.product_id, None), axis=1)

        else:
            products_df['product_name'] = None
            products_df['product_brand'] = None
            products_df['product_category'] = None
            products_df['entity_price'] = None

        cols = products_df.columns.tolist()
        cols = [cols[0]] + cols[-4:] + cols[1:-4]
        products_df = products_df[cols]

        output = io.BytesIO()

        # Create a workbook and add a worksheet.
        writer = pd.ExcelWriter(output, engine='xlsxwriter')

        headers = [
            'Producto ID',
            'Producto nombre',
            'Producto marca',
            'Categoría',
            'Precio oferta entidad',
            'Clicks total',
            'Clicks tienda',
            'Clicks porcentaje',
            'Precio sumado total',
            'Precio sumado tienda',
            'Precio sumado porcentaje',
            'Precio promedio total',
            'Precio promedio tienda',
            'Precio máximo total',
            'Precio máximo tienda',
            'Precio mínimo total',
            'Precio mínimo tienda',
        ]
        products_df.to_excel(writer, sheet_name='Sheet1', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10
        })

        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)

        format1 = workbook.add_format({'num_format': '#,##0'})
        format2 = workbook.add_format({'num_format': '0.00%'})

        for index, h in enumerate(headers):
            if 'porcentaje' in h:
                worksheet.set_column(index, index, None, format2)
            elif 'Precio' in h:
                worksheet.set_column(index, index, None, format1)

        workbook.close()

        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()
        path = storage.save('reports/store_analytics_{}.xlsx'.format(
            timezone.now().strftime('%Y-%m-%d_%H:%M:%S')),
            file_for_upload)
        filename = timezone.now().strftime('store_analytics_%Y-%m-%d_%H:%M:%S')

        return {
            'file': file_value,
            'filename': filename,
            'path': path
        }
