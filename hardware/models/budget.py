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
from solotodo.models import Product, Entity, EsProduct
from solotodo_core.s3utils import PrivateS3Boto3Storage, \
    MediaRootS3Boto3Storage
from storescraper.utils import HeadlessChrome


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

    def expanded_products_pool(self):
        # Returnes a "fixed" product pool of the budget that also considers
        # the "selected_product" of each entry
        products = list(self.products_pool.all())
        for entry in self.entries.filter(selected_product__isnull=False).select_related('selected_product'):
            products.append(entry.selected_product)
        return products

    def export(self, export_format):
        stores = [entry.selected_store for entry in
                  self.entries.filter(selected_store__isnull=False)
                      .select_related('selected_store')]

        entities = Entity.objects.filter(
            product__in=self.expanded_products_pool(),
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

    def remove_product(self, product):
        self.products_pool.remove(product)
        self.entries.filter(selected_product=product).update(
            selected_product=None,
            selected_store=None
        )

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

        s = EsProduct.search().filter(
                'terms', product_id=[e.id for e in selected_products])[
            :len(selected_products)]

        es_products_dict = {x['product_id']: x for x in s.execute()}
        es_products = [es_products_dict[p.id] for p in selected_products]

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
                errors.append('Tu cotización tiene más de un {}'.format(
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

        mb = None
        if motherboards:
            mb = motherboards[0]
        else:
            warnings.append("""
Tu cotización no incluye placa madre, que es necesaria para un PC.
Se ejecutarán las otras pruebas de compatibilidad
            """)

        case = None
        max_case_video_card_length = None
        if cases:
            case = cases[0]
            max_case_video_card_length = case.specs.max_video_card_length
        else:
            warnings.append("""
Tu cotización no incluye gabinete, que es necesario para un PC.
Se ejecutarán las otras pruebas de compatibilidad
            """)

        psu = None
        if psus:
            psu = psus[0]
        elif not case or case and not case.specs.power_supply_power:
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
            if video_card.specs.length > 0:
                if max_case_video_card_length:
                    if video_card.specs.length > max_case_video_card_length:
                        errors.append("""
La tarjeta de video excede el largo máximo permitido por el gabinete (La
tarjeta mide {} mm. y el gabinete aguanta hasta {} mm.)
                                    """.format(video_card.specs.length,
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
                    processor.specs.graphics_id != 105914

            motherboard_has_integrated_graphics = None
            if mb:
                # 130455 is No Posee, 130507 is
                # "redirige graficos del procesador"
                motherboard_has_integrated_graphics = \
                    mb.specs.chipset_northbridge_graphics_id not in [
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
            if vc1.specs.gpu_id != vc2.specs.gpu_id:
                errors.append("""
Para un arreglo SLI / CrossFire las tarjetas tienen que tener la misma GPU
                """)
            elif not vc1.specs.gpu_has_multi_gpu_support:
                errors.append("""
La {} no permite SLI / Crossfire
                """.format(vc1.specs.gpu_unicode))
            else:
                gpu_brand = vc1.specs.gpu_brand_unicode
                if gpu_brand == 'NVIDIA' and mb and \
                        not mb.specs.allows_sli:
                    errors.append("""
La placa madre no permite SLI
                    """)
                elif gpu_brand == 'AMD' and mb and \
                        not mb.specs.allows_cf:
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

        if processor and mb:
            default_cores = []

            for x in getattr(mb.specs, 'chipset_supported_processor_cores_by_default', []):
                default_cores.append(x.id)

            update_cores = []

            for x in getattr(mb.specs, 'chipset_supported_processor_cores_with_bios_update', []):
                update_cores.append(x.id)

            if processor.specs.socket_socket_id != \
                    mb.specs.chipset_northbridge_family_socket_socket_id:
                errors.append("""El procesador tiene que ser del mismo socket
que la placa madre. En tu cotización el procesador es socket {} y la placa
madre es socket {}
""".format(
                    processor.specs.socket_socket_unicode,
                    mb.specs.
                    chipset_northbridge_family_socket_socket_unicode))
            elif processor.specs.core_id in default_cores:
                # No problem, chipset supports the core by default
                pass
            elif processor.specs.core_id in update_cores:
                warnings.append("""
Para usar el procesador {} en la placa madre {} la placa madre puede que
requiera de actualización de BIOS previa, por favor confirme con la tienda
donde la vaya a comprar si es el caso y si la pueden entregar actualizada. \z\z

Para Chile, las tiendas que ofrecen el servicio de actualización de placas
madre actualmente son:

AllTec (gratis), Infor-Ingen (gratis), PC Express (gratis), TtChile (con un
costo adicional) y Winpy (con un costo adicional, seleccionando "Actualización
de BIOS en Placa Madre" en el carrito de compras de su sitio). \z\z

No tenemos información de la política de actualización de BIOS de las otras
tiendas en este momento. \z\z

Si prendes el PC con el procesador en la placa sin actualizar el equipo
probablemente no va a mostrar señal de video, y no va a mostrar BIOS.
""".format(processor.name, mb.name))
            else:
                errors.append("""
El chipset de la placa madre {} no soporta oficialmente el procesador {}. Es
posible esta placa madre en específico sea compatible con el procesador, pero
depende del modelo. Por favor confirma con la página oficial del fabricante
de la placa madre.
""".format(mb.name, processor.name))
        if processor and processor.specs.cooler_name == 'No posee' and not \
                cooler:
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

        if mb and case:
            try:
                motherboard_size_index = motherboard_formats_by_size.index(
                    mb.specs.format_format_id)
                case_size_index = motherboard_formats_by_size.index(
                    case.specs.largest_motherboard_format_format_id)

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
            if ram.specs.is_ecc or ram.specs.is_fully_buffered:
                errors.append("""
La RAM {} es de servidor, no de PC desktop
                """.format(ram.name))

        if mb:
            total_dimm_count = 0
            for ram in rams:
                total_dimm_count += ram.specs.capacity_dimm_quantity_value

            if total_dimm_count > mb.specs.memory_slots_quantity:
                errors.append("""
Tu cotización incluye {} sticks de RAM, pero la placa madre solo aguanta {}
                """.format(total_dimm_count,
                           mb.specs.memory_slots_quantity))

            for ram in rams:
                if ram.specs.bus_bus_bus_format_id != \
                        mb.specs.memory_slots_mtype_itype_format_id:
                    errors.append("""
La RAM {} es de formato {} pero la placa madre usa RAMs {}
                    """.format(
                        ram.name, ram.specs.bus_bus_bus_format_unicode,
                        mb.specs.memory_slots_mtype_itype_format_unicode))

                if ram.specs.bus_bus_bus_type_id != \
                        mb.specs.memory_slots_mtype_itype_type_id:
                    errors.append("""
            La RAM {} es de tipo {} pero la placa madre usa RAMs {}
                                """.format(
                        ram.name, ram.specs.bus_bus_bus_type_unicode,
                        mb.specs.memory_slots_mtype_itype_type_unicode))

            # If the motherboard is socket 1151 DDR3, warn the use of DDR3L
            # memory

            if mb.specs.chipset_northbridge_family_socket_socket_id == \
                    106523 and \
                    mb.specs.memory_slots_mtype_itype_type_id == 130770:
                warnings.append("""
Para las plataformas Intel socket 1151 DDR3 se recomienda el uso de RAM DDR3L
(DDR3 de 1.35V). El uso de RAM DDR3 estándar (DDR3 de 1.5V) puede afectar el
procesador con el paso del tiempo.
                """)

        # HDD

        if case:
            if len(hdds) > case.specs.internal_3_1_2_bays:
                errors.append("""
Tu cotización include {} discos duros pero el gabinete solo aguanta {}
                """.format(len(hdds), case.specs.internal_3_1_2_bays))

        for hdd in hdds:
            # If it is not SATA 1, 2 or 3, error
            if hdd.specs.bus_bus_id not in [130996, 131002, 131011]:
                errors.append("""
El disco duro {} no es para PCs desktop
                """.format(hdd.name))

            if hdd.specs.size_id == 204414:
                errors.append("""
El disco duro {} es para notebooks. Sirven en PCs desktop pero son más lentos
y tienen precios similares.
                """.format(hdd.name))

            # If it has less than 7200 RPM, warning
            if hdd.specs.rpm_value < 7200:
                warnings.append("""
El disco duro {} es de {} rpm. Por rendimiento es preferible usar uno de
 7200 rpm, además que usualmente tienen casi el mismo precio.
""".format(hdd.name, hdd.specs.rpm_value))

        # PSU

        if psu and case and case.specs.power_supply_power:
            warnings.append("""
Tu cotización incluye una fuente de poder, pero el gabinete ya incluye una.
Para gabinetes ATX estándar puedes cambiar la fuente incluida por otra, esto
es una observación solamente.
            """)

        if case and case.specs.power_supply_power and video_cards and not psu:
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
            for socket_group in cooler.specs.grouped_sockets:
                for socket in socket_group.sockets:
                    cooler_socket_ids.append(socket['id'])

            if mb:
                if mb.specs.chipset_northbridge_family_socket_socket_id \
                        not in cooler_socket_ids:
                    errors.append("""
El cooler no es compatible con el socket de la placa madre.
                    """)
            if processor and processor.specs.socket_socket_id not in \
                    cooler_socket_ids:
                errors.append("""
El cooler no es compatible con el socket del procesador.
                """)

            if case and case.specs.max_cpu_cooler_height:
                if cooler.specs.height > case.specs.max_cpu_cooler_height:
                    errors.append("""
El cooler no entra en el gabinete.
                """)

            if processor and processor.specs.cooler_unicode != 'No posee':
                warnings.append("""
Tu cotización incluye un cooler pero el procesador viene con un cooler
incluido. Puedes usar un cooler distinto al de fábrica pero usualmente no es
necesario.
                """)

        # SSD

        if mb and ssds:
            mb_available_ports = []
            for mb_has_port in mb.specs['storage_ports']:
                mb_available_ports.extend(
                    [mb_has_port] * mb_has_port.quantity)

            for ssd_hit in ssds:
                ssd = ssd_hit.specs.to_dict()

                warning_and_error_per_port = []
                for port in mb_available_ports:
                    local_warnings = []
                    local_errors = []

                    # Physical check

                    # 1559371 is the ID of the legacy "M.2" connector without
                    # information of its size (2280, 2242, 2230).
                    if ssd['ssd_type_connector_id'] == 1559371:
                        if 'M.2' in port['port_unicode']:
                            local_warnings.append("""
El SSD {} es de tipo M.2, pero no tenemos información de su tamaño (2280, 
2242, 2230) para verificar si es compatible fisicamente con la placa madre
""".format(ssd['unicode']))
                        else:
                            local_errors.append("""
El SSD {} es de tipo M.2 pero el puerto {} no es M.2""".format(ssd['unicode'], port['port_unicode']))

                    if port['port_connector_id'] == 1559371:
                        if 'M.2' in ssd['ssd_type_connector_unicode']:
                            local_warnings.append("""
El puerto de almacenamiento es de tipo M.2, pero no tenemos información de 
su tamaño (2280, 2242, 2230) para verificar si es compatible fisicamente con 
el ssd {}""".format(ssd['unicode']))
                        else:
                            local_errors.append("""
El puerto de almacenamiento es de tipo M.2 pero el SSD {} no es M.2
""".format(ssd['unicode']))

                    if ssd['ssd_type_connector_id'] != 1559371 and \
                            port['port_connector_id'] != 1559371:

                        port_additional_compat_ids = []
                        if 'port_connector_additional_compatibility' in port:
                            for x in port['port_connector_additional_compatibility']:
                                port_additional_compat_ids.append(x['id'])

                        if ssd['ssd_type_connector_id'] != port['port_connector_id'] and ssd['ssd_type_connector_id'] \
                                not in port_additional_compat_ids:
                            local_errors.append("""
El puerto {} no es físicamente compatible con el ssd {}""".format(port['port_unicode'], ssd['unicode']))

                    # Bus check

                    if 'port_buses' not in port:
                        # Assume it's the legacy M.2 MB port
                        if 'M.2' in ssd['ssd_type_connector_unicode']:
                            local_warnings.append("""
El puerto de almacenamiento es de tipo M.2, pero no tenemos información de su 
tipo (SATA, PCIe) para verificar si es eléctricamente compatible con el SSD {}
""".format(ssd['unicode']))
                        else:
                            local_errors.append("""
El puerto {} es de tipo M.2 pero el SSD {} no es M.2""".format(port['port_unicode'], ssd['unicode']))

                    buses_warnings_and_errors = []

                    for bus in getattr(port, 'port_buses', []):
                        bus_warnings = []
                        bus_errors = []

                        if bus['bus_with_version_id'] != ssd['ssd_type_bus_bus_with_version_id']:
                            bw_compatiblity_ids = []
                            for x in ssd.get('ssd_type_bus_bus_with_version_backwards_compatibility', []):
                                bw_compatiblity_ids.append(x['id'])

                            if bus['bus_with_version_id'] in bw_compatiblity_ids:
                                bus_warnings.append("""
El SSD {} es eléctricamente compatible con el puerto {}, pero es posible que 
no funcione al 100% de su rendimiento porque el puerto es de una versión PCIe 
más antigua. """.format(ssd['unicode'], port['port_unicode']))
                            else:
                                bus_errors.append("""
El bus del puerto {} es incompatible con el bus del SSD ({})
""".format(port['port_unicode'], ssd['ssd_type_unicode']))

                        # 1559281 is the id of the base PCIe, the lanes check
                        # should only be run in that case
                        if bus['bus_with_version_bus_id'] == 1559281 and \
                                ssd['ssd_type_bus_bus_with_version_bus_id'] == 1559281:
                            if bus['lanes'] == 1:
                                bus_warnings.append("""
No tenemos informacion de la cantidad de lanes PCIe disponibles en el bus {}, 
así que no podemos saber si el SSD va a funcionar a toda su capacidad en esta 
placa madre""".format(port['port_unicode']))
                            if ssd['ssd_type_bus_lanes'] == 1:
                                bus_warnings.append("""
No tenemos informacion de la cantidad de lanes PCIe utilizados por el SSD {}, 
así que no podemos saber si el SSD va a funcionar a toda su capacidad en esta 
placa madre""".format(ssd['unicode']))
                            if ssd['ssd_type_bus_lanes'] > bus['lanes'] > 1:
                                bus_warnings.append("""
El bus del puerto {} tiene menos lanes (x{}) que el SSD {} ({}), así que 
el SSD puede que no funcione a plena capacidad""".format(port['port_unicode'], bus['lanes'],
                                                         ssd['unicode'], ssd['ssd_type_bus_unicode']))

                        buses_warnings_and_errors.append({
                            'bus': bus,
                            'warnings': bus_warnings,
                            'errors': bus_errors
                        })

                    buses_warnings_and_errors.sort(
                        key=lambda x: (len(x['errors']), len(x['warnings'])))

                    if buses_warnings_and_errors:
                        best_bus = buses_warnings_and_errors[0]
                        local_errors.extend(best_bus['errors'])
                        local_warnings.extend(best_bus['warnings'])

                    warning_and_error_per_port.append({
                        'port': port,
                        'warnings': local_warnings,
                        'errors': local_errors
                    })

                warning_and_error_per_port.sort(
                    key=lambda x: (len(x['errors']), len(x['warnings'])))

                if warning_and_error_per_port:
                    best_port_entry = warning_and_error_per_port[0]
                    errors.extend(best_port_entry['errors'])
                    warnings.extend(best_port_entry['warnings'])
                    mb_available_ports.remove(best_port_entry['port'])
                else:
                    errors.append('No hay puertos disponible para el SSD '
                                  '{}'.format(ssd['unicode']))

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
            for port in monitor.specs.video_ports:
                if port.id in digital_video_port_ids:
                    has_digital_input = True
                    break
            else:
                has_digital_input = False

            if not has_digital_input:
                warnings.append("""
El monitor {} no tiene entradas de video digital (e.g. DVI, HDMI o
 DisplayPort). Las tarjetas de video actuales solo funcionan con esas entradas
 y no son compatibles con el puerto VGA.""".format(monitor.name))

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

        with HeadlessChrome() as driver:
            driver.set_window_size(1000, 1000)
            driver.get('file://{}'.format(filename))

            image = Image.open(BytesIO(base64.b64decode(
                driver.get_screenshot_as_base64())))
            # driver.close()

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
