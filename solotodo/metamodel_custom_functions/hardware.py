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


def additional_es_fields(instance_model, elastic_search_original):
    m = instance_model.model.name
    if m == 'Processor':
        result = {}
        result['has_turbo_frequencies'] = \
            elastic_search_original['max_turbo_frequency'] > \
            elastic_search_original['frequency']
        result['brand_unicode'] = \
            elastic_search_original['line_family_brand_brand_unicode']
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
        video_ports = elastic_search_original['video_ports_unicode']
        if video_ports:
            result['pretty_video_ports'] = \
                ' | '.join(str(vp) for vp in video_ports)
        else:
            result['pretty_video_ports'] = ' No posee'
        return result
    if m == 'Printer':
        result = {}
        networking = elastic_search_original.get('networking_unicode', None)
        if networking:
            result['pretty_networking'] = \
                ' | '.join(str(vp) for vp in networking)
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

#
# def additional_product_details_context(context, get_data, payment_methods,
#                                        stores, country):
#     additional_context = {}
#     is_product_hardware = context['product'].product_type.backend_name in \
#         settings.PRODUCT_TYPE_HARDWARE
#
#     additional_context['is_product_hardware'] = is_product_hardware
#
#     return additional_context
#
#
# def update_scores_gpu(instance_model):
#     instance_model.tdmark_11_score = get_tdmark_11_score(instance_model)
#     instance_model.tdmark_cloud_gate_score = \
#         get_tdmark_cloud_gate_score(instance_model)
#     instance_model.tdmark_fire_strike_score = \
#         get_tdmark_fire_strike_score(instance_model)
#
#
# def get_tdmark_11_score(instance_model):
#     return _get_tdmark_score(instance_model, '3dm11', 'P')
#
#
# def get_tdmark_cloud_gate_score(instance_model):
#     return _get_tdmark_score(instance_model, 'cg', 'P')
#
#
# def get_tdmark_fire_strike_score(instance_model):
#     return _get_tdmark_score(instance_model, 'fs', 'P')
#
#
# def _get_tdmark_score(instance_model, test_id, test_mode):
#     return get_futuremark_score(
#         instance_model.tdmark_id, 'gpu', test_id, test_mode)
#
#
# # Retrieves scores from FutureMark
# def get_futuremark_score(futuremark_id, component_code, test_id, test_mode):
#     import mechanize
#
#     if futuremark_id == '0':
#         return 0
#     base_url = 'http://www.3dmark.com'
#     args = '?minScore=1'
#
    # page_url = base_url + '/proxycon/ajax/search/{}/{}/{}/{}/2147483647/{}' \
    #                       ''.format(component_code, test_id, test_mode,
    #                                 futuremark_id, args)
#
#     browser = mechanize.Browser()
#
#     scores = []
#     while True:
#         data = browser.open(page_url).get_data()
#         json_data = json.loads(data)
#         for result in json_data['results']:
#             if result['gpuCount'] > 1:
#                 continue
#             scores.append(result['overallScore'])
#
#         try:
#             next_page_url = json_data['nextPageLink']
#         except KeyError:
#             break
#
#         if not next_page_url:
#             break
#
#         page_url = base_url + next_page_url + args
#
#     if not scores:
#         return 0
#
#     return sum(scores) / len(scores)
#
#
# def get_pcmark_7_score(instance_model):
#     return _get_pcmark_score(instance_model, 'pcm7')
#
#
# def get_pcmark_8_score(instance_model):
#     return _get_pcmark_score(instance_model, 'pcm8hm3', 'O')
#
#
# def _get_pcmark_score(instance_model, test_id, test_mode='D'):
#     return get_futuremark_score(
#         instance_model.pcmark_id, 'cpu', test_id, test_mode)
#
#
# def update_scores_cpu(instance_model):
#     instance_model.pcmark_7_score = get_pcmark_7_score(instance_model)
#     instance_model.pcmark_8_score = get_pcmark_8_score(instance_model)
