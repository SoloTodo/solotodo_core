from metamodel.models import MetaModel
from .utils import pretty_dimensions, format_optional_field


def pretty_video_ports(elastic_search_original):
    video_ports = elastic_search_original['video_ports']
    if video_ports:
        return ' | '.join(vp['unicode'] for vp in video_ports)
    else:
        return 'No posee'


def additional_es_fields(instance_model, elastic_search_original):
    m = instance_model.model.name
    big_value = 1000 * 1000 * 1000 * 100000
    result = {}
    if m == 'Camera':
        pretty_screen = elastic_search_original['screen_size_unicode']
        is_screen_touch = elastic_search_original['is_screen_touch']
        result['pretty_screen'] = pretty_screen
        if is_screen_touch:
            result['pretty_screen'] += u' táctil'

        result['pretty_dimensions'] = \
            pretty_dimensions(elastic_search_original)
        result['pretty_weight'] = format_optional_field(
            elastic_search_original['weight'], 'g')

        aperture_speed = elastic_search_original['aperture_speed']
        if aperture_speed:
            result['pretty_aperture_speed'] = \
                '1/{}'.format(aperture_speed)
        else:
            result['pretty_aperture_speed'] = 'Desconocido'

        result['model_name'] = \
            u'{} {}'.format(elastic_search_original['line_name'],
                            elastic_search_original['name']).strip()

        return result

    if m == 'Television':
        result['pretty_usb_ports'] = format_optional_field(
            elastic_search_original['usb_ports'], value_if_false='No posee')
        result['pretty_video_ports'] = \
            pretty_video_ports(elastic_search_original)
        result['model_name'] = u'{} {}'.format(
            elastic_search_original['line_name'],
            elastic_search_original['name']).strip()
        result['brand_unicode'] = elastic_search_original['line_brand_unicode']

        if elastic_search_original['display_unicode'] == 'OLED':
            lg_cac_segment = 'OLED'
        elif elastic_search_original['display_unicode'] == 'NanoCell':
            lg_cac_segment = 'NanoCell'
        elif elastic_search_original['size_family_value'] >= 70:
            lg_cac_segment = 'Ultra Large TV'
        elif elastic_search_original['resolution_id'] == 281518:
            lg_cac_segment = 'UHD'
        elif elastic_search_original['resolution_id'] == 281535:
            lg_cac_segment = 'Full HD'
        else:
            lg_cac_segment = 'LED'

        result['lg_cac_segment'] = lg_cac_segment

        return result

    if m == 'ExternalStorageDrive':
        result['pretty_weight'] = format_optional_field(
            elastic_search_original['weight'], 'g')

        return result

    if m == 'MemoryCard':
        result['pretty_part_number'] = format_optional_field(
            elastic_search_original['part_number'])
        return result

    if m == 'OpticalDiskPlayer':
        result['pretty_usb_ports'] = format_optional_field(
            elastic_search_original['usb_ports'], value_if_false='No posee')
        return result

    if m == 'Oven':
        result['pretty_dimensions'] = \
            pretty_dimensions(elastic_search_original)
        result['pretty_capacity'] = \
            format_optional_field(elastic_search_original['capacity'], 'L')
        return result

    if m == 'Refrigerator':
        result['pretty_refrigerator_capacity'] = \
            format_optional_field(
                elastic_search_original['refrigerator_capacity'], 'L')
        result['pretty_freezer_capacity'] = \
            format_optional_field(
                elastic_search_original['freezer_capacity'], 'L')
        result['pretty_dimensions'] = \
            pretty_dimensions(elastic_search_original)
        result['pretty_weight'] = format_optional_field(
            elastic_search_original['weight'], 'kg')

        total_capacity = \
            elastic_search_original['refrigerator_capacity'] + \
            elastic_search_original['freezer_capacity']

        result['total_capacity'] = total_capacity
        result['pretty_total_capacity'] = format_optional_field(
            total_capacity, 'L.')

        total_capacity_ranges = [
            ('600 L. o más', 600),
            ('350 a 599 L.', 350),
            ('300 a 349 L.', 300),
            ('299 L. o menos', 0),
        ]

        lg_cl_total_capacity_segment = None

        for label, threshold in total_capacity_ranges:
            if total_capacity >= threshold:
                lg_cl_total_capacity_segment = label
                break

        result['lg_cl_total_capacity_segment'] = lg_cl_total_capacity_segment
        consumption = elastic_search_original['consumption']
        result['pretty_consumption'] = format_optional_field(
            consumption, 'kWh/mes')
        if consumption > 0:
            result['sorting_consumption'] = consumption
        else:
            result['sorting_consumption'] = big_value
        return result

    if m == 'UsbFlashDrive':
        result['pretty_dimensions'] = \
            pretty_dimensions(elastic_search_original)
        result['pretty_part_number'] = format_optional_field(
            elastic_search_original['part_number'])

        read_speed = elastic_search_original['read_speed']
        result['pretty_read_speed'] = format_optional_field(read_speed, 'MB/s')

        write_speed = elastic_search_original['write_speed']
        result['pretty_write_speed'] = format_optional_field(
            write_speed, 'MB/s')

        return result

    if m == 'VacuumCleaner':
        result['pretty_dimensions'] = \
            pretty_dimensions(elastic_search_original)
        result['pretty_weight'] = format_optional_field(
            elastic_search_original['weight'], 'g')

        return result

    if m == 'WashingMachine':
        result['pretty_dimensions'] = \
            pretty_dimensions(elastic_search_original)
        result['pretty_weight'] = format_optional_field(
            elastic_search_original['weight'], 'g')
        weight = elastic_search_original['weight']
        if weight > 0:
            result['pretty_weight'] = u'{} kg.'.format(0.001*weight)
        else:
            result['pretty_weight'] = 'Desconocido'

        lg_cl_capacity = elastic_search_original['capacity_value'] or \
            elastic_search_original['drying_capacity_value']

        total_capacity_ranges = [
            ('20 kg. o más', 20000),
            ('16 a 19.9 kg.', 16000),
            ('10 a 15.9 kg.', 10000),
            ('9.9 kg. o menos', 0),
        ]

        lg_cl_capacity_segment = None

        for label, threshold in total_capacity_ranges:
            if lg_cl_capacity >= threshold:
                lg_cl_capacity_segment = label
                break

        result['lg_cl_capacity'] = lg_cl_capacity
        result['pretty_lg_cl_capacity'] = format_optional_field(
            round(lg_cl_capacity / 1000), 'kg.')
        result['lg_cl_capacity_segment'] = lg_cl_capacity_segment

        return result
    if m == 'AirConditioner':
        result['pretty_inner_dimensions'] = \
            pretty_dimensions(elastic_search_original,
                              ['inner_width', 'inner_height', 'inner_depth'])
        result['pretty_outer_dimensions'] = \
            pretty_dimensions(elastic_search_original,
                              ['outer_width', 'outer_height', 'outer_depth'])
    if m == 'WaterHeater':
        result['pretty_dimensions'] = \
            pretty_dimensions(elastic_search_original)
        return result

    if m == 'Stove':
        result['pretty_dimensions'] = \
            pretty_dimensions(elastic_search_original)
        result['pretty_weight'] = format_optional_field(
            elastic_search_original['weight'], 'g')
        return result

    if m == 'SpaceHeater':
        result['pretty_dimensions'] = \
            pretty_dimensions(elastic_search_original)

        unified_power = 0
        if elastic_search_original['power_w']:
            unified_power = elastic_search_original['power_w']
        elif elastic_search_original['power_kcal_hr']:
            unified_power = int(
                elastic_search_original['power_kcal_hr'] * 1.16222222)
        elif elastic_search_original['power_btu_hr']:
            unified_power = int(
                elastic_search_original['power_btu_hr'] * 0.29307107)

        result['unified_power'] = unified_power
        return result
    if m == 'VideoGameConsole':
        result['brand_unicode'] = \
            elastic_search_original['c_model_base_model_family_brand_unicode']
        return result
    if m == 'AllInOne':
        storage_unicodes = []

        for sd in elastic_search_original['storage_drives']:
            storage_unicodes.append(sd['unicode'])

            result['storage_unicode'] = ' + '.join(storage_unicodes)
        return result
    if m == 'Tablet':
        result['base_model_internal_storage_cell_connectivity_key'] = \
            elastic_search_original['base_model_id'] + \
            10 * elastic_search_original['internal_storage_id'] + \
            100 * elastic_search_original['cell_connectivity_id']

        result['pretty_dimensions'] = \
            pretty_dimensions(elastic_search_original,
                              ['length', 'width', 'depth'])
        battery_mah = \
            elastic_search_original['battery_mah']
        result['pretty_battery'] = \
            format_optional_field(battery_mah, 'mAh')
        result['model_name'] = \
            '{} {}'.format(elastic_search_original['line_name'],
                           elastic_search_original['name']).strip()

        # General score computation
        scores = []

        # Maxes based on current A12X Bionic scores (March 2020)
        score_fields = [
            ('geekbench_44_single_core_score', 5000),
            ('geekbench_44_multi_core_score', 18000),
            ('geekbench_5_single_core_score', 1200),
            ('geekbench_5_multi_core_score', 4700),
            ('passmark_score', 760000),
        ]

        for score_field, max_score in score_fields:
            field_name = 'soc_' + score_field

            if not elastic_search_original.get(field_name):
                continue

            relative_score = int(
                1000 * elastic_search_original.get(field_name, 0) / max_score)

            if relative_score > 1000:
                relative_score = 1000

            scores.append(relative_score)

        if scores:
            general_score = int(sum(scores) / len(scores))
        else:
            general_score = 0

        result['general_score'] = general_score

        return result

    if m == 'Wearable':
        if elastic_search_original['weight']:
            pretty_weight = '{} g.'.format(elastic_search_original['weight'])
        else:
            pretty_weight = 'Desconocido'

        result['pretty_weight'] = pretty_weight

        if elastic_search_original['battery_mah']:
            pretty_battery_mah = '{} mAh'.format(
                elastic_search_original['battery_mah'])
        else:
            pretty_battery_mah = 'Desconocido'

        result['pretty_battery_mah'] = pretty_battery_mah
        result['pretty_dimensions'] = pretty_dimensions(
            elastic_search_original)

    return result


def unicode_function(im):
    m = MetaModel.get_model_by_id(im.model_id).name
    if m == 'LightTube':
        specs = [str(im.l_type)]

        if im.consumption:
            if im.equivalent_power:
                specs.append(u'{} - {}W'.format(
                    im.consumption.quantize(0),
                    im.equivalent_power.quantize(0)))
            else:
                specs.append(u'{}W'.format(im.consumption.quantize(0)))
        else:
            if im.equivalent_power:
                specs.append(u'{}W Equivalente'.format(
                    im.equivalent_power.quantize(0)))

        specs.append(str(im.light_type))
        specs.append(str(im.length))

        name_value = im.name
        if name_value is None:
            name_value = ''

        result = u'{} {} {} ({})'.format(
            im.technology, im.brand, name_value, ' / '.join(specs))
        return ' '.join(result.split())
    if m == 'LightProjector':
        specs = []

        if im.consumption:
            if im.equivalent_power:
                specs.append(u'{} - {}W'.format(
                    im.consumption.quantize(0),
                    im.equivalent_power.quantize(0)))
            else:
                specs.append(u'{}W'.format(im.consumption.quantize(0)))
        else:
            if im.equivalent_power:
                specs.append(u'{}W Equivalente'.format(
                    im.equivalent_power.quantize(0)))

        specs.append(str(im.light_type))

        if im.has_movement_sensor:
            specs.append(u'Con sensor de movimimiento')

        name_value = im.name
        if name_value is None:
            name_value = ''

        result = u'{} {} {} ({})'.format(
            im.technology, im.brand, name_value, ' / '.join(specs))
        return ' '.join(result.split())
    if m == 'Lamp':
        specs = [str(im.socket), im.format.short_name]

        if im.consumption:
            if im.equivalent_power:
                specs.append(u'{} - {}W'.format(
                    im.consumption.quantize(0),
                    im.equivalent_power.quantize(0)))
            else:
                specs.append(u'{}W'.format(im.consumption.quantize(0)))
        else:
            if im.equivalent_power:
                specs.append(u'{}W Equivalente'.format(
                    im.equivalent_power.quantize(0)))

        specs.append(str(im.light_type))

        name_value = im.name
        if name_value is None:
            name_value = ''

        result = u'{} {} {} ({})'.format(
            im.l_type, im.brand, name_value, ' / '.join(specs))
        return ' '.join(result.split())
    if m == 'MemoryCardCapacity':
        if im.value % 1000 == 0:
            return u'{} TB'.format(im.value / 1000)
        elif im.value > 1000 and (im.value - 500) % 1000 == 0:
            return u'{}.5 TB'.format((im.value - 500) / 1000)
        else:
            return u'{} GB'.format(im.value)
    if m == 'MemoryCard':
        result = u'{} {} {}'.format(im.line, im.type, im.capacity)

        if im.rated_speed.value:
            result += u' {}'.format(im.rated_speed)
        elif im.x_speed.value:
            result += u' {}'.format(im.x_speed)

        if im.part_number:
            result += u' ({})'.format(im.part_number)

        return result
    if m == 'UsbFlashDriveCapacity':
        if im.value % 1000 == 0:
            return u'{} TB'.format(im.value / 1000)
        elif im.value > 1000 and (im.value - 500) % 1000 == 0:
            return u'{}.5 TB'.format((im.value - 500) / 1000)
        else:
            return u'{} GB'.format(im.value)
