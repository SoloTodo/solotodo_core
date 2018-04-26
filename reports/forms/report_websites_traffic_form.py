import io

import xlsxwriter
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Min, DateField, Count
from django.db.models.functions import Cast
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user

from category_columns.models import CategoryColumn
from solotodo.filter_utils import IsoDateTimeRangeField
from solotodo.models import Category, Store, Country, StoreType, Currency, \
    Entity, Product, EntityHistory, Website, Visit, Lead
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportWebsitesTrafficForm(forms.Form):
    timestamp = IsoDateTimeRangeField()
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False)
    stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all(),
        required=False)
    websites = forms.ModelMultipleChoiceField(
        queryset=Website.objects.all(),
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

        valid_categories = get_objects_for_user(user, 'view_category_reports',
                                                Category)
        self.fields['categories'].queryset = valid_categories

        valid_stores = get_objects_for_user(user, 'view_store_reports', Store)
        self.fields['stores'].queryset = valid_stores

        valid_websites = get_objects_for_user(user, 'view_website', Website)
        self.fields['websites'].queryset = valid_websites

    def clean_categories(self):
        selected_categories = self.cleaned_data['categories']
        if selected_categories:
            return selected_categories
        else:
            return self.fields['categories'].queryset

    def clean_stores(self):
        selected_stores = self.cleaned_data['stores']
        if selected_stores:
            return selected_stores
        else:
            return self.fields['stores'].queryset

    def clean_websites(self):
        selected_websites = self.cleaned_data['websites']
        if selected_websites:
            return selected_websites
        else:
            return self.fields['websites'].queryset

    def generate_report(self):
        categories = self.cleaned_data['categories']
        stores = self.cleaned_data['stores']
        websites = self.cleaned_data['websites']
        countries = self.cleaned_data['countries']
        store_types = self.cleaned_data['store_types']
        currency = self.cleaned_data['currency']
        timestamp = self.cleaned_data['timestamp']

        # Visits grouped by (product, date)

        visits = Visit.objects.filter(
            website__in=websites,
            timestamp__gte=timestamp.start,
            timestamp__lte=timestamp.stop,
            product__instance_model__model__category__in=categories
        ).annotate(date=Cast('timestamp', DateField()))\
            .order_by('product', 'date')\
            .values('product', 'date')\
            .annotate(visits=Count('pk'))

        visits_dict = {(visit['product'], visit['date']): visit['visits']
                       for visit in visits}

        leads = Lead.objects.filter(
            website__in=websites,
            timestamp__gte=timestamp.start,
            timestamp__lte=timestamp.stop,
            entity_history__entity__category__in=categories
        ).annotate(date=Cast('timestamp', DateField()))\
            .order_by('entity_history__entity', 'date')\
            .values('entity_history__entity', 'date')\
            .annotate(visits=Count('pk'))

        leads_dict = {(lead['entity_history__entity'], lead['date']):
                      lead['visits'] for lead in leads}

        ehs = EntityHistory.objects.filter(
            entity__product__instance_model__model__category__in=categories,
            entity__store__in=stores,
            timestamp__gte=timestamp.start,
            timestamp__lte=timestamp.stop,
        ).get_available().annotate(date=Cast('timestamp', DateField()))

        if countries:
            ehs = ehs.filter(entity__store__country__in=countries)

        if store_types:
            ehs = ehs.filter(entity__store__type__in=store_types)

        ehs = ehs.values('entity', 'date').annotate(
            min_normal_price=Min('normal_price'),
            min_offer_price=Min('offer_price'),
            min_cell_monthly_payment=Min('cell_monthly_payment')
        ).order_by('entity', 'date')

        entity_ids = [eh['entity'] for eh in ehs]
        entities = Entity.objects.filter(pk__in=entity_ids).select_related(
            'product__instance_model__model__category',
            'cell_plan__instance_model',
            'active_registry',
            'currency',
            'store'
        )
        entities_dict = {entity.id: entity for entity in entities}

        if categories.count() == 1:
            category = categories[0]

            product_ids = [x['entity__product']
                           for x in ehs.values('entity__product')]
            es_search = Product.es_search().filter(
                'terms', product_id=product_ids)
            es_dict = {e.product_id: e.to_dict()
                       for e in es_search[:100000].execute()}

            specs_columns = CategoryColumn.objects.filter(
                field__category=category,
                purpose=settings.REPORTS_PURPOSE_ID
            )
        else:
            category = None
            es_dict = None
            specs_columns = []

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

        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})

        headers = [
            'Producto',
        ]

        cell_plans_in_entities = [e.cell_plan for e in
                                  entities.filter(cell_plan__isnull=False)]

        if cell_plans_in_entities:
            headers.append('Plan celular')

        headers.extend([
            'Tienda',
            'SKU',
            'Condición',
            'Moneda',
            'Fecha',
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

        if category:
            headers.extend([column.field.label for column in specs_columns])
        else:
            headers.append('Categoría')

        headers.extend(['Visitas', 'Leads'])

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1
        for eh in ehs:
            col = 0
            entity = entities_dict[eh['entity']]

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
                    worksheet.write_url(
                        row, col,
                        '{}products/{}'.format(settings.BACKEND_HOST,
                                               cell_plan.id),
                        string=str(entity.cell_plan),
                        cell_format=url_format)
                else:
                    worksheet.write(row, col, 'N/A')

                col += 1

            # Store
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

            # Date
            worksheet.write_datetime(row, col, eh['date'], date_format)
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

            # Specs or category
            if category:
                es_entry = es_dict[entity.product_id]
                for column in specs_columns:
                    worksheet.write(row, col, es_entry.get(
                        column.field.es_field, 'N/A'))
                    col += 1
            else:
                worksheet.write(row, col, str(entity.product.category))
                col += 1

            # Visits
            visits = visits_dict.get((entity.product_id, eh['date']), 0)
            worksheet.write(row, col, visits)
            col += 1

            # Leads
            leads = leads_dict.get((entity.id, eh['date']), 0)
            worksheet.write(row, col, leads)
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
            filename_template = 'websites_traffic_%Y-%m-%d_%H:%M:%S'

        filename = timezone.now().strftime(filename_template)

        path = storage.save('reports/{}.xlsx'.format(filename),
                            file_for_upload)

        return {
            'file': file_value,
            'path': path
        }
