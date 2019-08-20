import io
from decimal import Decimal

import xlsxwriter
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.management import BaseCommand
from django.db.models import Min
from django.utils import timezone
from guardian.shortcuts import get_objects_for_group

from solotodo.models import Store, Entity
from solotodo_core.s3utils import PrivateS3Boto3Storage


class Command(BaseCommand):
    def handle(self, *args, **options):
        store = Store.objects.get(name='PC Factory')
        group = Group.objects.get(name='PC Factory')

        stores = get_objects_for_group(group, 'view_store', Store)
        pcf_entities = store.entity_set.filter(
            product__isnull=False
        ).get_available().select_related(
            'active_registry',
            'product__instance_model__model__category'
        )

        product_ids = [e['product_id'] for e in
                       pcf_entities.values('product_id')]

        stores_entities = Entity.objects.filter(
            store__in=stores,
            condition='https://schema.org/NewCondition',
            active_registry__cell_monthly_payment__isnull=True,
            store__type=1
        ).get_available()

        min_prices = stores_entities.filter(
            product__in=product_ids
        ).order_by('product').values('product').annotate(
            min_price=Min('active_registry__normal_price')
        )
        min_price_per_product = {
            e['product']: e['min_price'] for e in min_prices
        }

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)
        worksheet = workbook.add_worksheet()

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10
        })

        headers = [
            ('SKU', 9),
            ('Nombre SKU', 80),
            ('Producto', 80),
            ('Categoría', 20),
            ('Precio PC Factory', 20),
            ('Menor precio del mercado', 20),
            ('Diferencia (%)', 15),
            ('Tienda #1 con menor precio', 30),
            ('Tienda #2 con menor precio', 30),
            ('Tienda #3 con menor precio', 30),
        ]

        for idx, header_data in enumerate(headers):
            worksheet.write(0, idx, header_data[0], header_format)
            worksheet.set_column(idx, idx+1, header_data[1])

        row = 1

        pcf_entities = list(filter(
            lambda x: x.active_registry.normal_price >= Decimal('1.1') *
            min_price_per_product[x.product_id], pcf_entities))
        pcf_entities.sort(key=lambda x: x.active_registry.normal_price /
                          min_price_per_product[x.product_id],
                          reverse=True)

        for pcf_entity in pcf_entities:
            pcf_price = pcf_entity.active_registry.normal_price
            min_price = min_price_per_product[pcf_entity.product_id]

            worksheet.write_url(row, 0, pcf_entity.url,
                                string=pcf_entity.sku)
            worksheet.write(row, 1, pcf_entity.name)
            worksheet.write(row, 2, str(pcf_entity.product))
            worksheet.write(row, 3, str(pcf_entity.product.category))
            worksheet.write(row, 4, pcf_entity.active_registry.normal_price)
            worksheet.write(row, 5, min_price)

            percentage_delta = Decimal('100') * (pcf_price - min_price) / \
                min_price

            worksheet.write(row, 6, percentage_delta)

            best_price_entities = stores_entities.filter(
                product=pcf_entity.product,
                active_registry__normal_price=min_price
            ).select_related('store')[:3]

            col = 7

            for entity in best_price_entities:
                worksheet.write_url(row, col, entity.url,
                                    string=str(entity.store))
                col += 1

            row += 1

        worksheet.autofilter(0, 0, row - 1, len(headers) - 1)
        workbook.close()

        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()

        filename_template = 'pc_factory_%Y-%m-%d_%H:%M:%S'

        filename = timezone.now().strftime(filename_template)

        path = storage.save('reports/{}.xlsx'.format(filename),
                            file_for_upload)
        print(storage.url(path))
