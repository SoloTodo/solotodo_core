import io

import pytz
import xlsxwriter
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user

from category_columns.models import CategoryColumn
from solotodo.filter_utils import IsoDateTimeRangeField
from solotodo.models import Category, Store, Country, StoreType, Currency, \
    EntityHistory, EsProduct
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportPricesHistoryForm(forms.Form):
    timestamp = IsoDateTimeRangeField()
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
        required=False
    )
    timezone = forms.CharField(
        required=False
    )
    exclude_unavailable = forms.IntegerField(
        required=False
    )
    filename = forms.CharField(
        required=False
    )

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

    def clean_timezone(self):
        selected_timezone = self.cleaned_data['timezone']
        if selected_timezone:
            return selected_timezone
        else:
            return 'UTC'

    def generate_report(self):
        categories = self.cleaned_data['categories']
        stores = self.cleaned_data['stores']
        countries = self.cleaned_data['countries']
        store_types = self.cleaned_data['store_types']
        currency = self.cleaned_data['currency']
        timestamp = self.cleaned_data['timestamp']
        exclude_unavailable = self.cleaned_data['exclude_unavailable']
        report_timezone = pytz.timezone(self.cleaned_data['timezone'])

        ehs = EntityHistory.objects.filter(
            entity__product__instance_model__model__category__in=categories,
            entity__store__in=stores,
            timestamp__gte=timestamp.start,
            timestamp__lte=timestamp.stop,
        ).select_related(
            'entity__product__instance_model',
            'entity__cell_plan__instance_model',
            'entity__currency',
            'entity__store'
        )

        if countries:
            ehs = ehs.filter(entity__store__country__in=countries)

        if store_types:
            ehs = ehs.filter(entity__store__type__in=store_types)

        if exclude_unavailable:
            ehs = ehs.get_available()

        if categories.count() == 1:
            category = categories[0]

            product_ids = [x['entity__product']
                           for x in ehs.values('entity__product')]
            es_search = EsProduct.search().filter(
                'terms', product_id=product_ids)
            es_dict = {e.product_id: e.to_dict()
                       for e in es_search.scan()}

            specs_columns = CategoryColumn.objects.filter(
                field__category=category,
                purpose=settings.REPORTS_PURPOSE_ID,
                is_extended=False
            )
        else:
            category = None
            es_dict = None
            specs_columns = []

        output = io.BytesIO()

        # Create a workbook and add a worksheet.
        workbook = xlsxwriter.Workbook(output, {'remove_timezone': True})
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

        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        time_format = workbook.add_format({'num_format': 'hh:mm'})
        cell_plans_in_entities = [eh.entity.cell_plan for eh in
                                  ehs.filter(entity__cell_plan__isnull=False)]

        headers = [
            'Producto',
        ]

        if cell_plans_in_entities:
            headers.append('Plan celular')

        headers.extend([
            'Tienda',
            'SKU',
            'Condición',
            'Moneda',
            'Fecha',
            'Hora',
            'Precio normal',
            'Precio oferta',
            'Número reviews',
            'Puntaje reviews'
        ])

        cell_monthly_payments_in_entities = ehs.filter(
            cell_monthly_payment__isnull=False)

        if cell_monthly_payments_in_entities:
            if cell_plans_in_entities:
                headers.append('Cuota arriendo')

        if currency:
            headers.extend([
                'Precio normal ({})'.format(currency.iso_code),
                'Precio oferta ({})'.format(currency.iso_code),
            ])

        headers.append('Nombre en tienda')

        if category:
            headers.extend([column.field.label for column in specs_columns])
        else:
            headers.append('Categoría')

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1
        for eh in ehs:
            col = 0

            # Product

            worksheet.write_url(
                row, col,
                '{}products/{}'.format(settings.PRICING_HOST,
                                       eh.entity.product.id),
                string=str(eh.entity.product),
                cell_format=url_format)

            col += 1

            # Cell plan

            if cell_plans_in_entities:
                cell_plan = eh.entity.cell_plan
                if cell_plan:
                    worksheet.write_url(
                        row, col,
                        '{}products/{}'.format(settings.PRICING_HOST,
                                               cell_plan.id),
                        string=str(eh.entity.cell_plan),
                        cell_format=url_format)
                else:
                    worksheet.write(row, col, 'N/A')

                col += 1

            # Store

            worksheet.write(row, col, str(eh.entity.store))
            col += 1

            # SKU

            if eh.entity.sku:
                sku_text = str(eh.entity.sku)
            else:
                sku_text = 'N/A'

            worksheet.write_url(
                row, col,
                '{}skus/{}'.format(settings.PRICING_HOST, eh.entity.id),
                string=sku_text,
                cell_format=url_format)
            col += 1

            # Condition
            worksheet.write(row, col, str(eh.entity.condition_as_text))
            col += 1

            # Currency

            worksheet.write(row, col, str(eh.entity.currency.iso_code))
            col += 1

            # Date

            worksheet.write_datetime(row, col, eh.timestamp.astimezone(
                report_timezone), date_format)
            col += 1

            # Hour

            worksheet.write_datetime(row, col,
                                     eh.timestamp.astimezone(report_timezone),
                                     time_format)
            col += 1

            # Normal price

            worksheet.write(row, col, eh.normal_price)
            col += 1

            # Offer price

            worksheet.write(row, col, eh.offer_price)
            col += 1

            # Review count

            worksheet.write(row, col, eh.review_count or 'N/A')
            col += 1

            # Review score

            worksheet.write(row, col, eh.review_avg_score or 'N/A')
            col += 1

            # Cell monthly payment
            if cell_monthly_payments_in_entities:
                if eh.cell_monthly_payment is not None:
                    cell_monthly_payment_text = \
                        eh.cell_monthly_payment
                else:
                    cell_monthly_payment_text = 'No aplica'
                worksheet.write(row, col, cell_monthly_payment_text)
                col += 1

            # Converted prices
            if currency:
                converted_normal_price = currency.convert_from(
                    eh.normal_price, eh.entity.currency)
                worksheet.write(row, col, converted_normal_price)
                col += 1

                converted_offer_price = currency.convert_from(
                    eh.offer_price, eh.entity.currency)
                worksheet.write(row, col, converted_offer_price)
                col += 1

            # Store name
            worksheet.write(row, col, eh.entity.name)
            col += 1

            if category:
                es_entry = es_dict[eh.entity.product_id]
                for column in specs_columns:
                    worksheet.write(row, col, es_entry['specs'].get(
                        column.field.es_field, 'N/A'))
                    col += 1
            else:
                worksheet.write(row, col, str(eh.entity.product.category))
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
            filename_template = 'price_history_%Y-%m-%d_%H:%M:%S'

        filename = timezone.now().strftime(filename_template)

        path = storage.save('reports/{}.xlsx'.format(filename),
                            file_for_upload)

        return {
            'file': file_value,
            'path': path
        }
