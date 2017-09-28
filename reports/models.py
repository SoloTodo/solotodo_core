import io
import xlsxwriter
from django.core.files.base import ContentFile
from django.db import models

from solotodo.models import Entity, Product
from solotodo_try.s3utils import PrivateS3Boto3Storage


class Report(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    def render_current_prices(self, user):
        es = Entity.objects.filter(product__isnull=False)\
            .filter(category=1)\
            .get_available()\
            .filter_by_user_perms(user, 'view_entity')\
            .select_related()\
            .order_by('product')

        product_ids = [x['product'] for x in es.values('product')]

        es_search = Product.es_search().filter('terms', product_id=product_ids)
        es_dict = {e.product_id: e.to_dict()
                   for e in es_search[:100000].execute()}

        print(product_ids)

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

        es_fields = [
            ('Marca', 'line_brand_unicode'),
            ('Modelo', 'model_name'),
            (u'Línea Procesador', 'processor_line_unicode'),
            ('Procesador', 'processor_unicode'),
            ('RAM', 'ram_quantity_unicode'),
            ('Pantalla', 'screen_size_unicode'),
            (u'Resolución pantalla', 'screen_resolution_unicode'),
            ('Tarjeta de video integrada', 'processor_gpu_unicode'),
            ('Tarjeta de video dedicada', 'dedicated_video_card_unicode'),
            (u'Unidad óptica', 'optical_drive_unicode'),
            (u'Pantalla táctil', 'screen_is_touchscreen'),
            (u'Sistema operativo', 'operating_system_unicode'),
            (u'Sistema operativo (corto)', 'operating_system_short_name'),
            ('Tipo almacenamiento',
             'largest_storage_drive_drive_type_unicode'),
            ('Capacidad almacenamiento',
             'largest_storage_drive_capacity_unicode'),
            (u'Batería', 'pretty_battery'),
            ('Peso (g)', 'weight'),
            (u'Tamaño', 'pretty_dimensions'),
            ('Puertos de video', 'pretty_video_ports'),
            ('Bluetooth', 'has_bluetooth'),
            ('WiFi', 'wifi_card_unicode'),
            ('Puertos USB', 'usb_port_count'),
            ('Webcam (MP)', 'webcam_mp'),
            ('LAN', 'lan_unicode'),
            (u'Adaptador de energía', 'power_adapter_unicode'),
            ('Lector de tarjetas', 'card_reader_unicode'),
            (u'¿Lector de huellas?', 'has_fingerprint_reader')
        ]

        headers = [
            'Producto',
            'Categoría',
            'Tienda',
            'SKU',
            'Precio normal',
            'Precio oferta',
            'Nombre'
        ]

        headers.extend([e[0] for e in es_fields])

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1
        for e in es:
            es_entry = es_dict[e.product_id]
            print(e.id)

            worksheet.write_url(
                row, 0,
                'http://local.solotodo.com:3000/products/' + str(e.product.id),
                string=str(e.product),
                cell_format=url_format)
            worksheet.write(row, 1, str(e.category))
            worksheet.write(row, 2, str(e.store))
            worksheet.write_url(
                row, 3,
                'http://local.solotodo.com:3000/entities/' + str(e.id),
                string=e.sku,
                cell_format=url_format)
            worksheet.write(row, 4, e.active_registry.normal_price)
            worksheet.write(row, 5, e.active_registry.offer_price)
            worksheet.write(row, 6, e.name)

            col = 7
            for idx, field in enumerate(es_fields):
                worksheet.write(row, col + idx, es_entry.get(field[1], 'N/A'))

            row += 1

        worksheet.autofilter(0, 0, row-1, len(headers)-1)

        workbook.close()

        output.seek(0)
        file_for_upload = ContentFile(output.getvalue())

        storage = PrivateS3Boto3Storage()
        path = storage.save('reports/{}.xlsx'.format(self.name),
                            file_for_upload)

        return storage.url(path)

    class Meta:
        ordering = ('name',)
        permissions = (
            ('view_report', 'Can view the report'),
        )
