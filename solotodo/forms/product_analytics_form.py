from django import forms
from django_filters.fields import IsoDateTimeRangeField

from google.cloud import bigquery


class ProductAnalyticsForm(forms.Form):
    timestamp = IsoDateTimeRangeField()

    def generate_report(self, product):
        timestamp = self.cleaned_data['timestamp']

        start_date = timestamp.start.strftime('%Y%m%d')
        stop_date = timestamp.stop.strftime('%Y%m%d')

        query = f'''
            SELECT
                price,
                retailer_id,
            FROM
                (SELECT
                    (SELECT ep.value.int_value
                    FROM UNNEST(event_params) AS ep
                    WHERE ep.key = 'product_id') AS product_id,
                    (SELECT CASE WHEN ep.value.int_value is not null 
                    THEN ep.value.int_value ELSE ep.value.double_value END
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
                AND event_date <= '{stop_date}'
                )
            WHERE product_id = {product.id}
            AND price is not null
            AND condition = 'https://schema.org/NewCondition'
            ORDER BY price
        '''

        client = bigquery.Client()

        query_job = client.query(query)
        click_results = query_job.result()

        return click_results
