import io

import xlsxwriter
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Min
from django.db.models.functions import ExtractWeek, ExtractYear
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user

from category_columns.models import CategoryColumn
from solotodo.filter_utils import IsoDateTimeRangeField
from solotodo.models import Category, Store, Country, StoreType, Currency, \
    Entity, Product, EntityHistory
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportWeeklyPricesForm(forms.Form):
    timestamp = IsoDateTimeRangeField()
    category = forms.ModelChoiceField(
        queryset=Category.objects.all())
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
    filename = forms.CharField(
        required=False
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        valid_categories = get_objects_for_user(user, 'view_category',
                                                Category)
        self.fields['category'].queryset = valid_categories

        valid_stores = get_objects_for_user(user, 'view_store', Store)
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
        countries = self.cleaned_data['countries']
        store_types = self.cleaned_data['store_types']
        currency = self.cleaned_data['currency']
        timestamp = self.cleaned_data['timestamp']

        ehs = EntityHistory.objects.filter(
            entity__product__instance_model__model__category=category,
            entity__store__in=stores,
            timestamp__gte=timestamp.start,
            timestamp__lte=timestamp.stop,
        ).annotate(week=ExtractWeek('timestamp'),
                   year=ExtractYear('timestamp'))

        if countries:
            ehs = ehs.filter(entity__store__country__in=countries)

        if store_types:
            ehs = ehs.filter(entity__store__type__in=store_types)

        ehs = ehs.values('entity', 'year', 'week').annotate(
            min_normal_price=Min('normal_price'),
            min_offer_price=Min('offer_price'),
            min_cell_monthly_payment=Min('cell_monthly_payment')
        ).order_by('entity', 'year', 'week')

        entity_ids = [eh['entity'] for eh in ehs]
        entities = Entity.objects.filter(pk__in=entity_ids).select_related(
            'product__instance_model',
            'cell_plan__instance_model',
            'active_registry',
            'currency',
            'store'
        )
        entities_dict = {entity.id: entity for entity in entities}

        product_ids = [x['product'] for x in entities.values('product')]

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

        cell_plans_in_entities = [e.cell_plan for e in
                                  entities.filter(cell_plan__isnull=False)]

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
            'Tienda2',
            'SKU',
            'Condición',
            'Moneda',
            'Año Semana',
            'Año',
            'Semana',
            'Mín. precio normal',
            'Mín. precio oferta'
        ])

        cell_monthly_payments_in_entities = entities.filter(
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
        headers.extend([column.field.label for column in specs_columns])

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1
        for eh in ehs:
            col = 0
            entity = entities_dict[eh['entity']]
            es_entry = es_dict[entity.product_id]

            # Product

            worksheet.write_url(
                row, col,
                '{}products/{}'.format(settings.BACKEND_HOST,
                                       entity.product.id),
                string=str(entity.product),
                cell_format=url_format)

            col += 1

            # Cell plan

            if cell_plans_in_entities:
                cell_plan = entity.cell_plan
                if cell_plan:
                    cell_plan_price = cell_plan_prices_dict.get(
                        cell_plan.id, 'N/A')

                    worksheet.write_url(
                        row, col,
                        '{}products/{}'.format(settings.BACKEND_HOST,
                                               cell_plan.id),
                        string=str(entity.cell_plan),
                        cell_format=url_format)
                    worksheet.write(row, col + 1, cell_plan_price)
                else:
                    worksheet.write(row, col, 'N/A')
                    worksheet.write(row, col + 1, 'N/A')

                col += 2

            # Store

            worksheet.write(row, col, str(entity.store))
            col += 1

            # Store 2

            worksheet.write(row, col, str(entity.store))
            col += 1

            # SKU

            if entity.sku:
                sku_text = str(entity.sku)
            else:
                sku_text = 'N/A'

            worksheet.write_url(
                row, col,
                '{}entities/{}'.format(settings.BACKEND_HOST, entity.id),
                string=sku_text,
                cell_format=url_format)
            col += 1

            # Condition
            worksheet.write(row, col, str(entity.condition_as_text))
            col += 1

            # Currency

            worksheet.write(row, col, str(entity.currency.iso_code))
            col += 1

            # Year week

            worksheet.write(row, col, '{}-{}'.format(eh['year'], eh['week']))
            col += 1

            # Year

            worksheet.write(row, col, eh['year'])
            col += 1

            # Week

            worksheet.write(row, col, eh['week'])
            col += 1

            # Min normal price

            worksheet.write(row, col, eh['min_normal_price'])
            col += 1

            # Min offer price

            worksheet.write(row, col, eh['min_offer_price'])
            col += 1

            # Cell monthly payment
            if cell_monthly_payments_in_entities:
                if eh['min_cell_monthly_payment'] is not None:
                    cell_monthly_payment_text = \
                        eh['min_cell_monthly_payment']
                else:
                    cell_monthly_payment_text = 'No aplica'
                worksheet.write(row, col, cell_monthly_payment_text)
                col += 1

            # Converted prices
            if currency:
                converted_normal_price = currency.convert_from(
                    eh['min_normal_price'], entity.currency)
                worksheet.write(row, col, converted_normal_price)
                col += 1

                converted_offer_price = currency.convert_from(
                    eh['min_offer_price'], entity.currency)
                worksheet.write(row, col, converted_offer_price)
                col += 1

            # Store name
            worksheet.write(row, col, entity.name)
            col += 1

            for column in specs_columns:
                worksheet.write(row, col, es_entry.get(column.field.es_field,
                                                       'N/A'))
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
            filename_template = 'weekly_prices_%Y-%m-%d_%H:%M:%S'

        filename = timezone.now().strftime(filename_template)

        path = storage.save('reports/{}.xlsx'.format(filename),
                            file_for_upload)

        return {
            'file': file_value,
            'path': path
        }
