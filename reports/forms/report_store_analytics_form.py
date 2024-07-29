import io

from django import forms
from django.core.files.base import ContentFile
from django.utils import timezone
from django_filters.fields import IsoDateTimeRangeField
from google.cloud import bigquery
from guardian.shortcuts import get_objects_for_user
import pandas as pd

from category_columns.models import CategoryColumn
from solotodo.models import Category, Entity, Product, Store
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportStoreAnalyticsForm(forms.Form):
    store = forms.ModelChoiceField(queryset=Store.objects.all(), required=False)
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False)
    timestamp = IsoDateTimeRangeField()

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        valid_categories = get_objects_for_user(user, "view_category_reports", Category)
        valid_stores = get_objects_for_user(user, "view_store_reports", Store)

        self.fields["store"].queryset = valid_stores
        self.fields["category"].queryset = valid_categories

    def generate_report(self):
        selected_store = self.cleaned_data["store"]
        selected_category = self.cleaned_data["category"]
        timestamp = self.cleaned_data["timestamp"]

        start_date = timestamp.start.strftime("%Y%m%d")
        stop_date = timestamp.stop.strftime("%Y%m%d")

        select_cause = f"""
            product_id,
            count(*) as total_clicks,
            sum(price) as total_price_sum,
            min(price) as min_price,
            round(sum(price) / count(*)) as average_price,
        """
        if selected_store:
            retailer_case_count = (
                f"CASE WHEN retailer_id = {selected_store.id} THEN 1 ELSE NULL END"
            )
            retailer_case_price = (
                f"CASE WHEN retailer_id = {selected_store.id} THEN price ELSE 0 END"
            )
            select_cause += f"""
                count({retailer_case_count}) as retailer_clicks,
                round((count({retailer_case_count}) / count(*)), 4) as precentage_clicks,
                sum({retailer_case_price}) as retailer_sum,
                sum(price) - sum({retailer_case_price}) as diff,
                round((sum({retailer_case_price}) / sum(price)), 4) as percentage_sum,
                IFNULL(safe_divide(sum({retailer_case_price}), count({retailer_case_count})), 0) as retailer_average_price,
                min({retailer_case_price}) as retailer_min_price,
            """
            order_cause = "-diff"
        else:
            order_cause = "-total_price_sum"

        condition = "condition = 'https://schema.org/NewCondition'"
        if selected_category:
            condition += "AND category_id = " + str(selected_category.id)

        query = f"""
            SELECT
                {select_cause}
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
            WHERE {condition}
            GROUP BY product_id
            ORDER BY {order_cause};
        """

        client = bigquery.Client()

        query_job = client.query(query)
        products_df = query_job.to_dataframe()

        products = Product.objects.filter(
            pk__in=products_df["product_id"].to_list()
        ).select_related("instance_model__model__category", "brand")
        Product.prefetch_specs(products)

        current_product_ids = list(set([p.id for p in products]))

        products_df = products_df[products_df["product_id"].isin(current_product_ids)]

        es = (
            Entity.objects.filter(
                product__in=products_df["product_id"].to_list(),
                store=selected_store,
                active_registry__cell_monthly_payment__isnull=True,
            )
            .get_available()
            .select_related("product", "active_registry")
        )
        entity_dict = {}
        for e in es:
            entity_dict[e.product_id] = int(e.active_registry.offer_price)

        products_dict = {
            product.id: {
                "name": product.name,
                "category": product.category.name,
                "brand": product.brand.name,
                "specs": product.specs,
            }
            for product in products
        }

        products_df["product_name"] = products_df.apply(
            lambda x: products_dict[x.product_id]["name"], axis=1
        )
        products_df["product_brand"] = products_df.apply(
            lambda x: products_dict[x.product_id]["brand"], axis=1
        )
        products_df["product_category"] = products_df.apply(
            lambda x: products_dict[x.product_id]["category"], axis=1
        )
        products_df["entity_price"] = products_df.apply(
            lambda x: entity_dict.get(x.product_id, None), axis=1
        )

        # else:
        #     products_df['product_name'] = None
        #     products_df['product_brand'] = None
        #     products_df['product_category'] = None
        #     products_df['entity_price'] = None

        report_cols = [
            "product_id",
            "product_name",
            "product_brand",
            "product_category",
            "total_clicks",
            "total_price_sum",
            "average_price",
        ]

        if selected_store:
            report_cols.extend(
                [
                    "entity_price",
                    "retailer_clicks",
                    "precentage_clicks",
                    "retailer_sum",
                    "diff",
                    "percentage_sum",
                    "retailer_average_price",
                ]
            )

        if selected_category:
            spec_columns = CategoryColumn.objects.filter(
                field__category=selected_category, purpose__name="reports"
            ).select_related("field")
            for column in spec_columns:
                report_cols.append(column.field.es_field)
                products_df[column.field.es_field] = products_df.apply(
                    lambda x: products_dict[x.product_id]["specs"].get(
                        column.field.es_field, "N/A"
                    ),
                    axis=1,
                )
        else:
            spec_columns = []

        products_df = products_df[report_cols]

        output = io.BytesIO()

        # Create a workbook and add a worksheet.
        writer = pd.ExcelWriter(output, engine="xlsxwriter")

        headers = [
            "ID",
            "Nombre",
            "Marca",
            "Categoría",
            "Clicks",
            "Valorización",
            "Precio promedio",
        ]

        if selected_store:
            headers.extend(
                [
                    "Precio actual {}".format(selected_store),
                    "Clicks {}".format(selected_store),
                    "% Clicks",
                    "Valorización {}".format(selected_store),
                    "Valorización potencial",
                    "% Valorización",
                    "Precio promedio {}".format(selected_store),
                ]
            )

        for column in spec_columns:
            headers.append(column.field.label)

        products_df.to_excel(writer, sheet_name="Sheet1", index=False)
        workbook = writer.book
        worksheet = writer.sheets["Sheet1"]

        header_format = workbook.add_format({"bold": True, "font_size": 10})

        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)

        format1 = workbook.add_format({"num_format": "#,##0"})
        format2 = workbook.add_format({"num_format": "0.00%"})

        for index, h in enumerate(headers):
            if "%" in h:
                worksheet.set_column(index, index, None, format2)
            elif "Precio" in h or "Valorización" in h:
                worksheet.set_column(index, index, None, format1)

        workbook.close()

        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()
        path = storage.save(
            "reports/store_analytics_{}.xlsx".format(
                timezone.now().strftime("%Y-%m-%d_%H:%M:%S")
            ),
            file_for_upload,
        )
        filename = timezone.now().strftime("store_analytics_%Y-%m-%d_%H:%M:%S")

        return {"file": file_value, "filename": filename, "path": path}
