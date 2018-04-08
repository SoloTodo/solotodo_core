from metamodel.models import MetaModel
from solotodo.metamodel_custom_functions.utils import pretty_dimensions, \
    format_optional_field


def pretty_video_ports(elastic_search_original):
    video_ports = elastic_search_original['video_ports_unicode']
    if video_ports:
        return ' | '.join(str(vp) for vp in video_ports)
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
        return result

    if m == 'ExternalStorageDrive':
        result['pretty_dimensions'] = \
            pretty_dimensions(elastic_search_original)
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
            elastic_search_original['weight'], 'g')

        consumption = elastic_search_original['consumption']
        result['pretty_consumption'] = format_optional_field(
            consumption, 'kWh/mes')
        if consumption > 0:
            result['sorting_consumption'] = consumption
        else:
            result['sorting_consumption'] = big_value
        return result

    if m == 'StereoSystem':
        result['pretty_usb_ports'] = format_optional_field(
            elastic_search_original['usb_ports'], value_if_false='No posee')
        return result

    if m == 'UsbFlashDrive':
        result['pretty_dimensions'] = \
            pretty_dimensions(elastic_search_original)
        result['pretty_sku'] = format_optional_field(
            elastic_search_original['sku'])

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
    if m == 'UsbFlashDrive':
        if im.sku:
            return u'{} {} {} ({})'.format(
                im.line, im.name, im.capacity, im.sku)
        else:
            return u'{} {} {}'.format(
                im.line, im.name, im.capacity)
