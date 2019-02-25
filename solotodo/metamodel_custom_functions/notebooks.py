from decimal import Decimal

from solotodo.metamodel_custom_functions.utils import pretty_dimensions


def ordering_value(im):
    m = im.model.name
    if m == 'NotebookScreen':
        return im.size.size * 10 + \
            (im.resolution.horizontal * im.resolution.vertical) \
            / Decimal(1000000)

    if m == 'NotebookScreenResolution':
        return im.horizontal * im.vertical


def pretty_battery(elastic_dict):
    """
    Returns a prettified version of the battery data or a default message
    if no info is available
    """
    additions = []
    if elastic_dict['battery_mah'] > 0:
        additions.append('{} mAh'.format(elastic_dict['battery_mah']))
    if elastic_dict['battery_mv'] > 0:
        additions.append('{} mV'.format(elastic_dict['battery_mv']))
    if elastic_dict['battery_mwh'] > 0:
        additions.append('{} mWh'.format(elastic_dict['battery_mwh']))
    result = ' | '.join(additions)

    if 'battery_cells' in elastic_dict and elastic_dict['battery_cells'] > 0:
        if result:
            result = '(' + result + ')'

        result = '{} celdas {}'.format(elastic_dict['battery_cells'], result)

    if not result:
        result = 'No hay información disponible'

    return result


def pretty_video_ports(elastic_dict):
    """
    Returns a prettified version of the video ports of the notebook or a
    default message if no info is available
    """
    result = ' | '.join([vp for vp in elastic_dict['video_port_unicode']])

    if not result:
        result = 'No posee salidas'

    return result


def get_score_general(elastic_dict):
    """
    Calculates and returns the score of this notebook when running normal
    applications on a fictional scale from 0 to 1000, but that can
    overflow over 1000. Consider 1000 to be a reasonable maximum.
    """

    # Heuristical calculation based on the current scores in the DB
    processor_rating = min(elastic_dict['processor_speed_score'] / 11000.0,
                           1.0)
    ram_rating = min(float(elastic_dict['ram_quantity_value']) / 6.0, 1.0)
    return int(800 * processor_rating + 200 * ram_rating)


def get_score_games(elastic_dict):
    """
    Calculates and returns the score of this notebook when running 3D
    games on a fictional scale from 0 to 1000, but that can
    overflow over 1000. Consider 1000 to be a reasonable maximum.
    """

    # Heuristical calculation based on the current scores in the DB
    processor_rating = min(elastic_dict['processor_speed_score'] / 11000.0,
                           1.0)
    ram_rating = min(float(elastic_dict['ram_quantity_value']) / 6.0, 1.0)

    gpu = elastic_dict.get('processor_gpu_speed_score', 0)
    dedicated = 0
    if 'dedicated_video_card_id' in elastic_dict:
        dedicated = elastic_dict['dedicated_video_card_speed_score']

    video_card_score = max(gpu, dedicated)

    # In case of SLI or Crossfire consider the addition of the two
    # gpus with a penalty

    if elastic_dict['is_multi_gpu']:
        video_card_score = int(1.5 * video_card_score)

    # Heuristical calculation based on the current scores in the DB
    video_card_rating = min(video_card_score / 20000.0, 1.0)

    return int(200 * processor_rating +
               100 * ram_rating +
               700 * video_card_rating)


def get_score_mobility(elastic_dict):
    """
    Calculates and returns the score of this notebook regarding its
    mobility (size, weight, etc) on a fictional scale from 0 to 1000,
    but that can overflow over 1000. Consider 1000 to be a reasonable
    maximum.
    """

    # Heuristical calculations based on the current scores in the DB
    screen_rating = min(
        max(2.25 - 0.125 * float(elastic_dict['screen_size_size']), 0), 1.0)
    weight_rating = min(max((3000 - elastic_dict['weight']) / 2000.0, 0), 1.0)
    processor_rating = min(
        max((4 - elastic_dict['processor_consumption']) / 3.0, 0), 1.0)

    return int(400 * screen_rating +
               300 * weight_rating +
               300 * processor_rating)


def get_sugestions_parameters(elastic_search_result):
    searching_criteria = {}

    if elastic_search_result['score_games'] >= 450:
        searching_criteria['ordering'] = '-score_games'
    elif elastic_search_result['score_mobility'] >= 700:
        searching_criteria['ordering'] = '-score_mobility'
        searching_criteria['max_screen_size'] = \
            elastic_search_result['screen_size_family_id']
        searching_criteria['min_screen_size'] = \
            elastic_search_result['screen_size_family_id']
    else:
        searching_criteria['ordering'] = '-score_general'

    return searching_criteria


def additional_es_fields(instance_model, elastic_search_result):
    m = instance_model.model.name

    if m == 'Notebook':
        result = {}

        video_cards_id = []
        video_cards_unicode = []

        if elastic_search_result['is_multi_gpu']:
            dedicated_video_card_es = \
                instance_model.dedicated_video_card.elasticsearch_document()[0]

            for key, value in dedicated_video_card_es.items():
                result[u'video_cards_' + key] = [value] * 2
                if key == u'id':
                    video_cards_id.extend([value] * 2)
                elif key == u'unicode':
                    video_cards_unicode.extend([value] * 2)

            pretty_dedicated_video_card = \
                elastic_search_result['dedicated_video_card_unicode']
        else:
            if 'processor_gpu_id' in elastic_search_result:
                integrated_gpu_result = \
                    instance_model.processor.gpu.elasticsearch_document()[0]

                for key, value in integrated_gpu_result.items():
                    result[u'video_cards_' + key] = [value]
                    if key == u'id':
                        video_cards_id.append(value)
                    elif key == u'unicode':
                        video_cards_unicode.append(value)

            if 'dedicated_video_card_id' in elastic_search_result:
                subresult = instance_model.dedicated_video_card\
                    .elasticsearch_document()[0]

                for key, value in subresult.items():
                    es_key = u'video_cards_' + key
                    if es_key in result:
                        result[es_key].append(value)
                    else:
                        result[es_key] = value

                    if key == u'id':
                        video_cards_id.append(value)
                    elif key == u'unicode':
                        video_cards_unicode.append(value)

                pretty_dedicated_video_card = \
                    elastic_search_result['dedicated_video_card_unicode']
            else:
                pretty_dedicated_video_card = 'No posee'

        result['pretty_battery'] = pretty_battery(
            elastic_search_result)
        result['pretty_ram'] = '{} {} ({})'.format(
            elastic_search_result['ram_quantity_unicode'],
            elastic_search_result['ram_type_unicode'],
            elastic_search_result['ram_frequency_unicode'])
        result['pretty_dimensions'] = \
            pretty_dimensions(elastic_search_result,
                              ['width', 'height', 'thickness'])
        result['pretty_video_ports'] = \
            pretty_video_ports(elastic_search_result)
        result['model_name'] = '{} {}'.format(
            elastic_search_result['line_name'],
            elastic_search_result['name'],
        ).strip()
        result[u'pretty_dedicated_video_card'] = pretty_dedicated_video_card
        result['video_cards_id_unicode'] = {id: value for id, value in
                                            zip(video_cards_id,
                                                video_cards_unicode)}

        result['score_general'] = get_score_general(elastic_search_result)
        result['score_games'] = get_score_games(elastic_search_result)
        result['score_mobility'] = get_score_mobility(elastic_search_result)

        elastic_search_result['score_games'] = result['score_games']
        elastic_search_result['score_mobility'] = result['score_mobility']
        result['suggested_alternatives_parameters'] = \
            get_sugestions_parameters(elastic_search_result)

        storage_drives = zip(
            elastic_search_result['storage_drive_drive_type_unicode'],
            elastic_search_result['storage_drive_capacity_value'],
            elastic_search_result['storage_drive_capacity_unicode'])

        storage_drives = sorted(storage_drives, key=lambda x: x[1],
                                reverse=True)

        result['largest_storage_drive_capacity_unicode'] = \
            storage_drives[0][2]
        result['largest_storage_drive_drive_type_unicode'] = \
            storage_drives[0][0]

        return result
