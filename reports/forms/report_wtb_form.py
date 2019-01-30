import io

import xlsxwriter
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Min
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user

from category_columns.models import CategoryColumn
from wtb.models import WtbBrand, WtbEntity
from solotodo.models import Category, Product, Entity
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportWtbForm(forms.Form):
    wtb_brand = forms.ModelChoiceField(
        queryset=WtbBrand.objects.all())
    category = forms.ModelChoiceField(
        queryset=Category.objects.all())

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, *kwargs)
        valid_categories = get_objects_for_user(user, 'view_category_reports',
                                                Category)
        self.fields['category'].queryset = valid_categories

    def generate_report(self):
        category = self.cleaned_data['category']
        wtb_brand = self.cleaned_data['wtb_brand']

        product_ids = []
        product_dict = {}

        wtb_entities = WtbEntity.objects.filter(brand=wtb_brand,
                                                category=category)

        for wtb_entity in wtb_entities:
            if wtb_entity.product_id not in product_dict:
                product_dict[wtb_entity.product_id] = wtb_entity
                product_ids.append(wtb_entity.product_id)

        es = Entity.objects.filter(product__in=product_ids)\
            .get_available()\
            .select_related(
            'product__instance_model',
            'cell_plan__instance_model',
            'active_registry',
            'currency',
            'store__country')\
            .order_by('product')

        es_search = Product.es_search().filter('terms', product_id=product_ids)
        es_dict = {e.product_id: e.to_dict()
                   for e in es_search[:100000].execute()}

        output = io.BytesIO()

        # Create a workbook and add a worksheet
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})

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
                                  es.filter(cell_plan__isnull=False)]

        headers = [
            'Identificador',
            'Nombre',
            'Producto'
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
            'País',
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

        headers.append('Nombre en tienda')
        headers.extend([column.field.label for column in specs_columns])

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1

        for e in es:
            col = 0
            es_entry = es_dict[e.product_id]

            # Wtb

            worksheet.write(
                row, col,
                product_dict[e.product.id].key)

            col += 1

            worksheet.write_url(
                row, col,
                product_dict[e.product.id].url,
                string=product_dict[e.product.id].name,
                cell_format=url_format)

            col += 1

            # Product

            worksheet.write_url(
                row, col,
                '{}products/{}'.format(settings.BACKEND_HOST, e.product.id),
                string=str(e.product),
                cell_format=url_format)

            col += 1

            # Cell plan

            if cell_plans_in_entities:
                cell_plan = e.cell_plan
                if cell_plan:
                    cell_plan_price = cell_plan_prices_dict.get(
                        cell_plan.id, 'N/A')

                    worksheet.write_url(
                        row, col,
                        '{}products/{}'.format(settings.BACKEND_HOST,
                                               cell_plan.id),
                        string=str(e.cell_plan),
                        cell_format=url_format)
                    worksheet.write(row, col + 1, cell_plan_price)
                else:
                    worksheet.write(row, col, 'N/A')
                    worksheet.write(row, col + 1, 'N/A')

                col += 2

            # Store

            worksheet.write(row, col, str(e.store))
            col += 1

            # Country

            worksheet.write(row, col, str(e.store.country))
            col += 1

            # SKU

            if e.sku:
                sku_text = str(e.sku)
            else:
                sku_text = 'N/A'

            worksheet.write_url(
                row, col,
                '{}entities/{}'.format(settings.BACKEND_HOST, e.id),
                string=sku_text,
                cell_format=url_format)
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

            # Store name
            worksheet.write(row, col, e.name)
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

        filename_template = 'wtb_report_%Y-%m-%d_%H:%M:%S'

        filename = timezone.now().strftime(filename_template)

        path = storage.save('reports/{}.xlsx'.format(filename),
                            file_for_upload)



        return {
            'file': file_value,
            'path': path
        }
