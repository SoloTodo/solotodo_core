import base64
import io
import re

import os
from io import BytesIO

import xlsxwriter
from decimal import Decimal

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import models
from django.template.loader import render_to_string
from django.utils.text import slugify
from selenium import webdriver

from metamodel.utils import trim, convert_image_to_inmemoryfile
from solotodo.models import Product, Entity
from solotodo_core.s3utils import PrivateS3Boto3Storage, \
    MediaRootS3Boto3Storage


class Budget(models.Model):
    name = models.CharField(max_length=255)
    is_public = models.BooleanField(default=False)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE,
                             related_name='budgets')
    creation_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    products_pool = models.ManyToManyField(Product, blank=True)

    def __str__(self):
        return self.name

    def export(self, stores, export_format):
        entities = Entity.objects.filter(
            product__in=self.products_pool.all(),
            store__in=stores
        ).get_available() \
            .order_by('active_registry__offer_price') \
            .select_related('store__country__number_format',
                            'product__instance_model',
                            'active_registry', 'currency',
                            'category')

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

    def compatibility_issues(self):
        """
        Checks if the selected parts in the budget are compatible between them,
        and returns a list of warnings and errors related to it.

        Errors are strict incompatibilities between two or more of the selected
        parts (e.g. the user has a motherboard and processor with different
        sockets)

        Warnings are observations like:
        * Missing parts: we assume that the user already has them, but notify
        that they are required for a functional computer
        * Unnecessary parts, for example adding a cpu cooler to a budget that
        uses a processor with an included cooler.
        :return:
        """
        warnings = []
        errors = []

        entries = self.entries.filter(
            selected_product__isnull=False).select_related(
                'selected_product__instance_model__model__category')

        selected_products = [e.selected_product for e in entries]

        s = Product.es_search().filter(
                'terms', product_id=[e.id for e in selected_products])[
            :len(selected_products)]

        es_products = s.execute()

        products_dict = {
            p.id: p.category.storescraper_name for p in selected_products
        }

        def filter_products(storescraper_name):
            return list(filter(
                lambda e: products_dict[e.product_id] == storescraper_name,
                es_products))

        video_cards = filter_products('VideoCard')
        processors = filter_products('Processor')
        motherboards = filter_products('Motherboard')
        rams = filter_products('Ram')
        hdds = filter_products('StorageDrive')
        psus = filter_products('PowerSupply')
        cases = filter_products('ComputerCase')
        ssds = filter_products('SolidStateDrive')
        coolers = filter_products('CpuCooler')
        monitors = filter_products('Monitor')

        # First test, we need 0 or 1 processor, motherboard, psu, case, and
        # cooler
        single_components = [
            (processors, 'procesador'),
            (motherboards, 'placa madre'),
            (psus, 'fuente de poder'),
            (cases, 'gabinete'),
            (coolers, 'cooler de procesador'),
        ]

        for component_list, component_name in single_components:
            if len(component_list) > 1:
                errors.append(u'Tu cotización tiene más de un {}'.format(
                    component_name))
                return warnings, errors

        # If there are 0 of some of these components, warn
        processor = None
        if processors:
            processor = processors[0]
        else:
            warnings.append("""
Tu cotización no incluye procesador, que es necesario para un PC.
Se ejecutarán las otras pruebas de compatibilidad
            """)

        motherboard = None
        if motherboards:
            motherboard = motherboards[0]
        else:
            warnings.append("""
Tu cotización no incluye placa madre, que es necesaria para un PC.
Se ejecutarán las otras pruebas de compatibilidad
            """)

        case = None
        max_case_video_card_length = None
        if cases:
            case = cases[0]
            max_case_video_card_length = case.max_video_card_length
        else:
            warnings.append("""
Tu cotización no incluye gabinete, que es necesario para un PC.
Se ejecutarán las otras pruebas de compatibilidad
            """)

        psu = None
        if psus:
            psu = psus[0]
        elif not case or case and not case.power_supply_power:
            warnings.append("""
Tu cotización no incluye fuente de poder, que es necesaria para un PC.
Se ejecutarán las otras pruebas de compatibilidad
            """)

        if not rams:
            warnings.append("""
Tu cotización no incluye RAM, que es necesaria para un PC.
Se ejecutarán las otras pruebas de compatibilidad
            """)

        if not ssds and not hdds:
            warnings.append("""
        Tu cotización no incluye almacenamiento (SSD o disco duro), que es
        necesario para un PC. Se ejecutarán las otras pruebas de compatibilidad
                    """)

        cooler = None
        if coolers:
            cooler = coolers[0]

        # Check video card compatibility
        # TODO: Check that the power supply has the necessary connectors

        def check_video_card_length(video_card):
            if video_card.length > 0:
                if max_case_video_card_length:
                    if video_card.length > max_case_video_card_length:
                        errors.append("""
La tarjeta de video excede el largo máximo permitido por el gabinete (La
tarjeta mide {} mm. y el gabinete aguanta hasta {} mm.)
                                    """.format(video_card.length,
                                               max_case_video_card_length))
                elif max_case_video_card_length == 0:
                    warnings.append("""
No hay información del largo máximo de tarjeta de video que acepta el gabinete
así que no se puede verificar su compatibilidad.
                            """)
            else:
                warnings.append("""
No hay información del largo de la tarjeta de video así que no se puede
verificar su compatibilidad con el gabinete.
                            """)

        if not video_cards:
            processor_has_integrated_graphics = None
            if processor:
                processor_has_integrated_graphics = \
                    processor.graphics_id != 105914

            motherboard_has_integrated_graphics = None
            if motherboard:
                # 130455 is No Posee, 130507 is
                # "redirige graficos del procesador"
                motherboard_has_integrated_graphics = \
                    motherboard.chipset_northbridge_graphics_id not in [
                        130455, 130507]

            if processor_has_integrated_graphics is False and \
                    motherboard_has_integrated_graphics is False:
                errors.append("""
Tu cotización no tiene tarjeta de video y la plataforma (procesador /
placa madre) no tiene gráficos integrados
                """)
        elif len(video_cards) == 1:
            video_card = video_cards[0]
            check_video_card_length(video_card)
        elif len(video_cards) == 2:
            # SLI / Crossfire
            vc1 = video_cards[0]
            vc2 = video_cards[1]

            # Check that the cards have the same GPU
            if vc1.gpu_id != vc2.gpu_id:
                errors.append("""
Para un arreglo SLI / CrossFire las tarjetas tienen que tener la misma GPU
                """)
            elif not vc1.gpu_has_multi_gpu_support:
                errors.append("""
La {} no permite SLI / Crossfire
                """.format(vc1.gpu_unicode))
            else:
                gpu_brand = vc1.gpu_brand_unicode
                if gpu_brand == 'NVIDIA' and motherboard and \
                        not motherboard.allows_sli:
                    errors.append("""
La placa madre no permite SLI
                    """)
                elif gpu_brand == 'AMD' and motherboard and \
                        not motherboard.allows_cf:
                    errors.append("""
                La placa madre no permite CrossFireX
                                    """)

                if vc1.product_id != vc2.product_id:
                    warnings.append("""
Es preferible hacer SLI o Crossfire con tarjetas de exactamente el mismo modelo
                    """)

                check_video_card_length(vc1)
                check_video_card_length(vc2)
        else:
            warnings.append("""
El sistema solo puede verificar la compatibilidad de 0, 1 o 2 tarjetas de video
            """)

        # Processor check
        # TODO Check if the processor / motherboard is for overclocking

        if processor and motherboard:
            if processor.socket_socket_id != \
                    motherboard.chipset_northbridge_family_socket_socket_id:
                errors.append("""El procesador tiene que ser del mismo socket
que la placa madre. En tu cotización el procesador es socket {} y la placa
madre es socket {}
""".format(
                    processor.socket_socket_unicode,
                    motherboard.
                    chipset_northbridge_family_socket_socket_unicode))

            # Check for Kaby Lake processor in Skylake motherboard

            if processor.core_id == 566207 and motherboard.chipset_id in \
                    [134521, 508999, 504945, 134630, 134639, 134847]:
                if motherboard.product_id == 31746:
                    warnings.append("""
La MSI H110M PRO-VH PLUS viene actualizada para usar procesadores Intel de
 séptima generación en las tiendas AllTec, SpDigital, y Winpy. No es seguro si
 las otras tiendas la entregan actualizada.
                    """)
                else:
                    warnings.append("""
Para usar un procesador Intel de séptima generación (Kaby Lake) en una placa de
 sexta generación (chipset H110 / B150 / H170 / Z170) la placa madre
 tiene que tener su BIOS actualizada ANTES de colocar el procesador. La
 única excepción actualmente es la MSI H110M PRO-VH PLUS que viene actualizada
 de fábrica por lo menos en las tiendas AllTec, SpDigital, y Winpy. \z\z

Para solucionar esto tienes tres opciones:\z\z

1. Comprar una placa madre compatible de fábrica (chipset B250 / H270 / Z270) o
 la H110M PRO-VH PLUS mencionada antes.\z
2. Pedir a la tienda donde la compres que te entregue la placa madre
actualizada (consulta a la tienda, no todas lo hacen, y algunas cobran extra)\z
3. Comprar la placa y llevarla a una tienda que actualice BIOS (TTChile,
Infor-Ingen). Las tiendas cobran por este servicio.\z\z

Si prendes el PC con el procesador en la placa sin actualizar el equipo no
 va a mostrar señal de video, y no va a mostrar BIOS.
""")

        if processor and not processor.includes_cooler and not cooler:
            errors.append("""
El procesador de tu cotización no incluye cooler de fábrica, y tu cotización
no considera un cooler dedicado.
            """)

        # Motherboard check
        # TODO: Check that the power supply has the necessary connectors
        # TODO: Check if the motherbord / processor are for overclocking

        itx_format = 130643
        micro_atx_format = 130612
        atx_format = 130631
        eatx_format = 130648

        motherboard_formats_by_size = [
            itx_format, micro_atx_format, atx_format, eatx_format
        ]

        if motherboard and case:
            try:
                motherboard_size_index = motherboard_formats_by_size.index(
                    motherboard.format_format_id)
                case_size_index = motherboard_formats_by_size.index(
                    case.largest_motherboard_format_format_id)

                if motherboard_size_index > case_size_index:
                    errors.append("""
La placa madre no entra en el gabinete, el formato del gabinete (ITX,
Micro ATX, ATX, Extended ATX) tiene que ser más grande que el de la
placa madre.
                    """)
            except ValueError:
                warnings.append("""
La placa madre y/o gabinete tienen un tamaño no estándar, así que no se puede
verificar si son compatibles.
                """)

        # RAM check

        for ram in rams:
            if ram.is_ecc or ram.is_fully_buffered:
                errors.append("""
La RAM {} es de servidor, no de PC desktop
                """.format(ram.unicode))

        if motherboard:
            total_dimm_count = 0
            for ram in rams:
                total_dimm_count += ram.capacity_dimm_quantity_value

            if total_dimm_count > motherboard.memory_slots_quantity:
                errors.append("""
Tu cotización incluye {} sticks de RAM, pero la placa madre solo aguanta {}
                """.format(total_dimm_count,
                           motherboard.memory_slots_quantity))

            for ram in rams:
                if ram.bus_bus_bus_format_id != \
                        motherboard.memory_slots_mtype_itype_format_id:
                    errors.append("""
La RAM {} es de formato {} pero la placa madre usa RAMs {}
                    """.format(
                        ram.unicode, ram.bus_bus_bus_format_unicode,
                        motherboard.memory_slots_mtype_itype_format_unicode))

                if ram.bus_bus_bus_type_id != \
                        motherboard.memory_slots_mtype_itype_type_id:
                    errors.append("""
            La RAM {} es de tipo {} pero la placa madre usa RAMs {}
                                """.format(
                        ram.unicode, ram.bus_bus_bus_type_unicode,
                        motherboard.memory_slots_mtype_itype_type_unicode))

            # If the motherboard is socket 1151 DDR3, warn the use of DDR3L
            # memory

            if motherboard.chipset_northbridge_family_socket_socket_id == \
                    106523 and \
                    motherboard.memory_slots_mtype_itype_type_id == 130770:
                warnings.append("""
Para las plataformas Intel socket 1151 DDR3 se recomienda el uso de RAM DDR3L
(DDR3 de 1.35V). El uso de RAM DDR3 estándar (DDR3 de 1.5V) puede afectar el
procesador con el paso del tiempo.
                """)

        # HDD

        if case:
            if len(hdds) > case.internal_3_1_2_bays:
                errors.append("""
Tu cotización include {} discos duros pero el gabinete solo aguanta {}
                """.format(len(hdds), case.internal_3_1_2_bays))

        for hdd in hdds:
            # If it is not SATA 1, 2 or 3, error
            if hdd.bus_bus_id not in [130996, 131002, 131011]:
                errors.append("""
El disco duro {} no es para PCs desktop
                """.format(hdd.unicode))

            if hdd.size_id == 204414:
                errors.append("""
El disco duro {} es para notebooks. Sirven en PCs desktop pero son más lentos
y tienen precios similares.
                """.format(hdd.unicode))

            # If it has less than 7200 RPM, warning
            if hdd.rpm_value < 7200:
                warnings.append("""
El disco duro {} es de {} rpm. Por rendimiento es preferible usar uno de
 7200 rpm, además que usualmente tienen casi el mismo precio.
""".format(hdd.unicode, hdd.rpm_value))

        # PSU

        if psu and case and case.power_supply_power:
            warnings.append("""
Tu cotización incluye una fuente de poder, pero el gabinete ya incluye una.
Para gabinetes ATX estándar puedes cambiar la fuente incluida por otra, esto
es una observación solamente.
            """)

        if case and case.power_supply_power and video_cards and not psu:
            warnings.append("""
Para equipos con tarjeta de video dedicada se recomienda comprar una fuente de
poder de buena calidad, las incluidas con los gabinetes usualmente no son
buenas.
            """)

        # Case

        # TODO Check if the case / video card are low profile

        # Cooler

        if cooler:
            cooler_socket_ids = []
            for socket_ids in cooler.grouped_sockets_sockets_socket_id:
                cooler_socket_ids.extend(list(socket_ids))

            if motherboard:
                if motherboard.chipset_northbridge_family_socket_socket_id \
                        not in cooler_socket_ids:
                    errors.append("""
El cooler no es compatible con el socket de la placa madre.
                    """)
            if processor and processor.socket_socket_id not in \
                    cooler_socket_ids:
                errors.append("""
El cooler no es compatible con el socket del procesador.
                """)

            if case and case.max_cpu_cooler_height:
                if cooler.height > case.max_cpu_cooler_height:
                    errors.append("""
El cooler no entra en el gabinete.
                """)

            if processor and processor.includes_cooler:
                warnings.append("""
Tu cotización incluye un cooler pero el procesador viene con un cooler
incluido. Puedes usar un cooler distinto al de fábrica pero usualmente no es
necesario.
                """)

        # SSD

        # TODO: Check if the SSDs are M.2 and the mothearboard has
        # M.2 slots. But in this case there are SATA and PCIe
        # SSDs...

        # Monitors

        digital_video_port_ids = [
            105894,  # DisplayPort
            105908,  # DVI
            105935,  # HDMI
            105952,  # Micro HDMI
            105959,  # Mini DisplayPort
            105978,  # Mini HDMI
            106001,  # Thunderbolt
        ]
        for monitor in monitors:
            has_digital_input = False
            for port_id in digital_video_port_ids:
                if port_id in monitor.video_ports_port_port_id:
                    has_digital_input = True
                    break

            if not has_digital_input:
                warnings.append("""
El monitor {} no tiene entradas de video digital (e.g. DVI, HDMI o
 DisplayPort). Las tarjetas de video actuales solo funcionan con esas entradas
 y no son compatibles con el puerto VGA.""".format(monitor.unicode))

        warnings = [' '.join(e.split()).replace('\z', '\n') for e in
                    warnings]
        errors = [' '.join(e.split()).replace('\z', '\n') for e in errors]

        return {
            'warnings': warnings,
            'errors': errors
        }

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
                'selected_product__instance_model', 'selected_store',
                'category'):
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

    def _export_as_bbcode(self, product_store_to_cheapest_entity_dict):
        context = self.__bbcode_and_img_context(
            product_store_to_cheapest_entity_dict)

        bbcode = render_to_string('budget_export_bbcode.txt', context)
        bbcode = re.sub(r'\s+', ' ', bbcode)

        return bbcode

    def _export_as_img(self, product_store_to_cheapest_entity_dict):
        context = self.__bbcode_and_img_context(
            product_store_to_cheapest_entity_dict)
        rendered_html = render_to_string('budget_export_img.html', context)

        filename = '/tmp/{}.html'.format(self.id)
        f = open(filename, 'w')
        f.write(rendered_html)
        f.close()

        driver = webdriver.PhantomJS()
        driver.set_window_size(1000, 1000)
        driver.get('file://{}'.format(filename))

        image = Image.open(BytesIO(base64.b64decode(
            driver.get_screenshot_as_base64())))
        driver.close()

        new_filename = 'budget_screenshots/{}.png'.format(self.id)
        file_to_upload = convert_image_to_inmemoryfile(trim(image))
        storage = MediaRootS3Boto3Storage()
        screenshot_path = storage.save(new_filename, file_to_upload)
        screenshot_url = storage.url(screenshot_path)

        os.remove(filename)

        return screenshot_url

    def __bbcode_and_img_context(self, product_store_to_cheapest_entity_dict):
        budget_entries = []

        currency = None
        number_format = None
        offer_price_sum = Decimal(0)
        normal_price_sum = Decimal(0)

        for entry in self.entries.select_related(
                'selected_product__instance_model', 'selected_store',
                'category'):
            key = (entry.selected_product, entry.selected_store)
            matching_entity = product_store_to_cheapest_entity_dict.get(key)

            if matching_entity:
                currency = matching_entity.currency
                number_format = matching_entity.store.country.number_format
                formatted_offer_price = currency.format_value(
                    matching_entity.active_registry.offer_price, number_format)
                formatted_normal_price = currency.format_value(
                    matching_entity.active_registry.normal_price,
                    number_format)

                offer_price_sum += matching_entity.active_registry.offer_price
                normal_price_sum += \
                    matching_entity.active_registry.normal_price
            else:
                formatted_offer_price = 'N/A'
                formatted_normal_price = 'N/A'

            budget_entries.append({
                'entry': entry,
                'entity': matching_entity,
                'offer_price': formatted_offer_price,
                'normal_price': formatted_normal_price,
            })

        # Usually budgets will have the same currency for all components, so
        # just use the last one seen to format the total.

        if currency:
            formatted_offer_price_sum = currency.format_value(
                offer_price_sum, number_format)
            formatted_normal_price_sum = currency.format_value(
                normal_price_sum, number_format)
        else:
            formatted_offer_price_sum = 'N/A'
            formatted_normal_price_sum = 'N/A'

        return {
            'budget': self,
            'budget_entries': budget_entries,
            'offer_price_sum': formatted_offer_price_sum,
            'normal_price_sum': formatted_normal_price_sum,
        }

    class Meta:
        app_label = 'hardware'
        ordering = ['-pk']
