import io

import xlsxwriter
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import models
from django.utils.text import slugify

from solotodo.models import Product, Entity
from solotodo_core.s3utils import PrivateS3Boto3Storage


class Budget(models.Model):
    name = models.CharField(max_length=255)
    is_public = models.BooleanField(default=False)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE,
                             related_name='budgets')
    creation_date = models.DateTimeField(auto_now_add=True)
    products_pool = models.ManyToManyField(Product, blank=True)

    def __str__(self):
        return self.name

    def export(self, stores, export_format):
        entities = Entity.objects.filter(
            product__in=self.products_pool.all(),
            store__in=stores
        ).get_available() \
            .order_by('active_registry__offer_price') \
            .select_related('store', 'product__instance_model',
                            'active_registry', 'currency')

        product_store_to_cheapest_entity_dict = {}

        for entity in entities:
            key = (entity.product, entity.store)
            if key not in product_store_to_cheapest_entity_dict:
                product_store_to_cheapest_entity_dict[key] = entity

        if export_format == 'xls':
            return self._export_as_xls(product_store_to_cheapest_entity_dict)
        elif export_format == 'bbcode':
            return self._export_as_bbcode(
                product_store_to_cheapest_entity_dict)
        elif export_format == 'img':
            return self._export_as_img(
                product_store_to_cheapest_entity_dict)
        else:
            raise Exception('Invalid format')

    def select_cheapest_stores(self, stores):
        entities = Entity.objects.filter(
            product__in=self.products_pool.all(),
            store__in=stores
        ).get_available() \
            .order_by('active_registry__offer_price') \
            .select_related('product')

        product_to_cheapest_store_dict = {}

        for entity in entities:
            if entity.product not in product_to_cheapest_store_dict:
                product_to_cheapest_store_dict[entity.product] = entity.store

        for budget_entry in self.entries.filter(
                selected_product__isnull=False):
            new_selected_store = product_to_cheapest_store_dict.get(
                budget_entry.selected_product)
            if budget_entry.selected_store != new_selected_store:
                budget_entry.selected_store = new_selected_store
                budget_entry.save()

    def _export_as_xls(self, product_store_to_cheapest_entity_dict):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        standard_format = workbook.add_format({
            'font_name': 'Verdana',
            'font_size': 10
        })

        header_format = workbook.add_format({
            'font_name': 'Verdana',
            'font_size': 10,
            'bold': True
        })

        currency_to_money_format = {}

        worksheet = workbook.add_worksheet()
        row = 0

        for idx, header in enumerate(['Componente', 'Producto', 'Tienda',
                                      'Precio oferta', 'Precio normal']):
            worksheet.write(row, idx, header, header_format)

        row += 1

        normal_price_sum = Decimal(0)
        offer_price_sum = Decimal(0)

        COMPONENT_COLUMN, PRODUCT_COLUMN, STORE_COLUMN, OFFER_PRICE_COLUMN, \
            NORMAL_PRICE_COLUMN = range(5)

        worksheet.set_column(COMPONENT_COLUMN, COMPONENT_COLUMN, 30)
        worksheet.set_column(PRODUCT_COLUMN, PRODUCT_COLUMN, 80)
        worksheet.set_column(STORE_COLUMN, STORE_COLUMN, 15)
        worksheet.set_column(OFFER_PRICE_COLUMN, OFFER_PRICE_COLUMN, 15)
        worksheet.set_column(NORMAL_PRICE_COLUMN, NORMAL_PRICE_COLUMN, 15)

        for entry in self.entries.select_related(
                'selected_product__instance_model', 'selected_store'):
            worksheet.write(row, COMPONENT_COLUMN, str(entry.category),
                            standard_format)

            if entry.selected_product:
                worksheet.write_url(
                    row,
                    PRODUCT_COLUMN,
                    entry.selected_product.solotodo_com_url(),
                    string=str(entry.selected_product),
                    cell_format=standard_format)
            else:
                worksheet.write(row, PRODUCT_COLUMN, 'N/A', standard_format)

            matching_entity = product_store_to_cheapest_entity_dict.get(
                (entry.selected_product, entry.selected_store)
            )

            if entry.selected_store:
                if matching_entity:
                    worksheet.write_url(
                        row,
                        STORE_COLUMN,
                        matching_entity.url,
                        string=str(entry.selected_store),
                        cell_format=standard_format)
                else:
                    worksheet.write(row, STORE_COLUMN,
                                    str(entry.selected_store), standard_format)
            else:
                worksheet.write(row, STORE_COLUMN, 'N/A', standard_format)

            if matching_entity:
                money_format = currency_to_money_format.get(
                    matching_entity.currency)
                if not money_format:
                    money_format = workbook.add_format({
                        'font_name': 'Verdana',
                        'font_size': 10,
                        'num_format': matching_entity.currency.excel_format()
                    })
                    currency_to_money_format[matching_entity.currency] = \
                        money_format

                worksheet.write(row, OFFER_PRICE_COLUMN,
                                matching_entity.active_registry.offer_price,
                                money_format)
                worksheet.write(row, NORMAL_PRICE_COLUMN,
                                matching_entity.active_registry.normal_price,
                                money_format)

                offer_price_sum += matching_entity.active_registry.offer_price
                normal_price_sum += \
                    matching_entity.active_registry.normal_price
            else:
                worksheet.write(row, OFFER_PRICE_COLUMN, 'N/A',
                                standard_format)
                worksheet.write(row, NORMAL_PRICE_COLUMN, 'N/A',
                                standard_format)

            row += 1

        worksheet.write(row, STORE_COLUMN, 'Total', header_format)

        if currency_to_money_format:
            # Most likely all of the entries are oof the same currency, so
            # using the "first" one should be safe
            currency = list(currency_to_money_format.keys())[0]

            bold_money_format = workbook.add_format({
                'font_name': 'Verdana',
                'font_size': 10,
                'bold': True,
                'num_format': currency.excel_format()
            })

            worksheet.write(row, OFFER_PRICE_COLUMN, offer_price_sum,
                            bold_money_format)
            worksheet.write(row, NORMAL_PRICE_COLUMN, normal_price_sum,
                            bold_money_format)
        else:
            worksheet.write(row, OFFER_PRICE_COLUMN, 'N/A', header_format)
            worksheet.write(row, NORMAL_PRICE_COLUMN, 'N/A', header_format)

        workbook.close()

        output.seek(0)
        file_for_upload = ContentFile(output.getvalue())

        storage = PrivateS3Boto3Storage()

        path = storage.save('budgets/exports/{}.xlsx'.format(
            slugify(self.name)), file_for_upload)
        budget_url = storage.url(path)

        return budget_url

    class Meta:
        app_label = 'hardware'
        ordering = ['-pk']
