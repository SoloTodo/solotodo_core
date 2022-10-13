# coding=utf-8
from metamodel.models import MetaModel

from solotodo.metamodel_custom_functions.utils import pretty_dimensions, \
    format_optional_field


def unicode_function(im):
    m = MetaModel.get_model_by_id(im.model_id).name
    if m == 'VideoCardMemoryQuantity':
        value = im.value
        if value % 1024 == 0:
            return '{} GB'.format(value / 1024)
        elif value > 512 and (value - 512) % 1024 == 0:
            return '{}.5 GB'.format((value - 512) / 1024)
        else:
            return '{} MB'.format(value)


def additional_es_fields(elastic_search_original, model_name):
    m = model_name
    if m == 'VideoCard':
        result = {
            'display_core_clock':
                elastic_search_original['core_clock'] >
                elastic_search_original['gpu_boost_core_clock'],
            'display_memory_clock':
                elastic_search_original['memory_clock'] -
                elastic_search_original['gpu_default_memory_clock'] >= 10
        }
        return result
    if m == 'Processor':
        result = {}
        result['has_turbo_frequencies'] = \
            elastic_search_original['max_turbo_frequency'] > \
            elastic_search_original['frequency']
        result['brand_unicode'] = \
            elastic_search_original['line_family_brand_brand_unicode']
        result['total_core_count'] = \
            elastic_search_original['core_count_value'] + \
            elastic_search_original['e_core_count_value']
        return result
    if m == 'PowerSupply':
        result = {}
        current = elastic_search_original['currents_on_12V_rails']
        if current == '0' or current == '':
            result['currents_on_12V_rails_unicode'] = []
        else:
            result['currents_on_12V_rails_unicode'] = current.split(',')
        return result
    big_value = 1000 * 1000 * 1000 * 10
    if m == 'ComputerCase':
        result = {}
        length = elastic_search_original['length']
        height = elastic_search_original['height']
        width = elastic_search_original['width']
        if length > 0 and height > 0 and width > 0:
            result['size_unicode'] = '{} x {} x {} mm.'.format(
                length, height, width)
            result['sorting_volume'] = length * height * width
        else:
            result['size_unicode'] = 'Desconocido'
            result['sorting_volume'] = big_value

        weight = elastic_search_original['weight']
        if weight > 0:
            result['sorting_weight'] = weight
        else:
            result['sorting_weight'] = big_value

        included_fan_count = 0
        for included_fan in elastic_search_original.get('included_fans', []):
            included_fan_count += included_fan['quantity']
        result['included_fan_count'] = included_fan_count

        return result
    if m == 'CpuCooler':
        result = {}
        noise = elastic_search_original['max_noise']
        weight = elastic_search_original['weight']
        if noise > 0:
            result['sorting_max_noise'] = noise
        else:
            result['sorting_max_noise'] = big_value
        if weight > 0:
            result['sorting_weight'] = weight
        else:
            result['sorting_weight'] = big_value
        return result

    if m == 'SolidStateDrive':
        result = {}

        sequential_read_speed = \
            elastic_search_original['sequential_read_speed']
        result['pretty_sequential_read_speed'] = \
            format_optional_field(sequential_read_speed, 'MB/s')

        sequential_write_speed = \
            elastic_search_original['sequential_write_speed']
        result['pretty_sequential_write_speed'] = \
            format_optional_field(sequential_write_speed, 'MB/s')

        return result
    if m == 'Monitor':
        result = {}
        contrast = elastic_search_original['contrast']
        if contrast:
            result['pretty_contrast'] = '{}:1'.format(contrast)
        else:
            result['pretty_contrast'] = 'Desconocido'
        brightness = elastic_search_original['brightness']
        if brightness:
            result['pretty_brightness'] = \
                '{} cd/m<sup>2</sup>'.format(brightness)
        else:
            result['pretty_brightness'] = 'Desconocido'
        video_ports = elastic_search_original['video_ports']
        if video_ports:
            result['pretty_video_ports'] = \
                ' | '.join(vp['unicode'] for vp in video_ports)
        else:
            result['pretty_video_ports'] = ' No posee'
        return result
    if m == 'Printer':
        result = {}
        networking = elastic_search_original.get('networking', None)
        if networking:
            result['pretty_networking'] = \
                ' | '.join(vp['unicode'] for vp in networking)
        else:
            result['pretty_networking'] = 'No posee'

        result['model_name'] = \
            '{} {}'.format(elastic_search_original['line_name'],
                           elastic_search_original['name']).strip()
        return result
    if m == 'Mouse':
        result = {}
        length = elastic_search_original['length']
        height = elastic_search_original['height']
        width = elastic_search_original['width']
        if length > 0 and height > 0 and width > 0:
            result['size_unicode'] = '{} x {} x {} mm.'.format(
                length, height, width)
            result['sorting_volume'] = length * height * width
        else:
            result['size_unicode'] = 'Desconocido'
            result['sorting_volume'] = big_value

        weight = elastic_search_original['weight']
        if weight > 0:
            result['sorting_weight'] = weight
        else:
            result['sorting_weight'] = big_value
        return result

    if m == 'Ram':
        result = {}
        heat_spreader = elastic_search_original['heat_spreader_unicode']

        if heat_spreader == 'Desconocido':
            segment = 'Desconocido'
        elif heat_spreader == 'No posee':
            segment = 'Value'
        else:
            segment = 'Gamer'

        result['segment'] = segment

        return result
