from decimal import Decimal


def pretty_cell_battery(cell):
    if cell['battery_mah']:
        result = '{} mAh'.format(cell['battery_mah'])
    else:
        result = 'N/A'

    return result


def cell_grouped_networks(cell):
    result = []
    subresult = []
    last_generation_seen = None
    for idx, network_unicode in enumerate(cell['networks_unicode']):
        if last_generation_seen is not None and \
                        cell['networks_generation_unicode'][idx] != \
                        last_generation_seen:
            result.append('{}: {} MHz'.format(
                last_generation_seen, ' / '.join(subresult)))
            subresult = []

        subresult.append(cell['networks_name'][idx])
        last_generation_seen = cell['networks_generation_unicode'][idx]

    # Add the trailing network, if it exists
    if last_generation_seen is not None:
        result.append('{}: {} MHz'.format(
            last_generation_seen, ' / '.join(subresult)))

    return result


def cell_plan_main_points(elastic_search_result):
    def cell_plan_navigation_quota_pretty_display(value):
        if value:
            if value >= 1000:
                value = Decimal(value) / Decimal(1000)
                return '{} GB de datos'.format(value.quantize(Decimal('0.1')))
            else:
                return '{} MB de datos'.format(value)
        else:
            return 'Sin plan de datos'

    result = [cell_plan_navigation_quota_pretty_display(
        elastic_search_result['navigation_quota_value'])]
    if elastic_search_result['minutes_free']:
        if elastic_search_result['minutes_free'] == -1:
            result.append('Minutos ilimitados todo destino')
        else:
            result.append('{} minutos todo destino'.format(
                elastic_search_result['minutes_free']))
    if elastic_search_result['sms_free']:
        if elastic_search_result['sms_free'] == -1:
            result.append('SMS ilimitados todo destino')
        else:
            result.append('{} SMS todo destino'.format(
                elastic_search_result['sms_free']))

    if elastic_search_result['portability_exclusive']:
        result.append('Plan exclusivo para portabilidad')
    return result


def additional_es_fields(instance_model, elastic_search_result):
    m = instance_model.model.name

    if m == 'Cell':
        result = {
            'pretty_battery': pretty_cell_battery(elastic_search_result),
            'grouped_networks': cell_grouped_networks(elastic_search_result),
            'model_name': '{} {}'.format(
                elastic_search_result['line_name'] or '',
                elastic_search_result['name']).strip(),
            'base_model_with_internal_storage': '{} - {}'.format(
                elastic_search_result['base_model_unicode'],
                elastic_search_result['internal_storage_unicode']
            )
        }

        if elastic_search_result['battery_mah']:
            result['pretty_battery_mah'] = '{} mAh'.format(
                elastic_search_result['battery_mah'])
        else:
            result['pretty_battery_mah'] = 'N/A'

        if elastic_search_result['weight']:
            result['pretty_weight'] = '{} g.'.format(
                elastic_search_result['weight'])
        else:
            result['pretty_weight'] = 'N/A'

        base_model_with_bundle = elastic_search_result['base_model_unicode']

        if elastic_search_result['bundle_unicode'].lower() != 'sin bundle':
            base_model_with_bundle += ' + {}'.format(
                elastic_search_result['bundle_unicode'])
            result['model_name'] += ' + {}'.format(
                elastic_search_result['bundle_unicode'])

        result['base_model_with_bundle'] = base_model_with_bundle

        result['base_model_bundle_internal_storage_ram_key'] = \
            elastic_search_result['base_model_id'] + \
            10 * elastic_search_result['bundle_id'] + \
            100 * elastic_search_result['internal_storage_id'] + \
            1000 * elastic_search_result['ram_id']

        if elastic_search_result['back_camera_value']:
            back_camera = '{} MP'.format(
                elastic_search_result['back_camera_value'])
            if 'back_camera_secondary_value' in elastic_search_result:
                back_camera += ' + {} MP'.format(
                    elastic_search_result['back_camera_secondary_value'])
            if 'back_camera_tertiary_value' in elastic_search_result:
                back_camera += ' + {} MP'.format(
                    elastic_search_result['back_camera_tertiary_value'])
            if 'back_camera_quaternary_value' in elastic_search_result:
                back_camera += ' + {} MP'.format(
                    elastic_search_result['back_camera_quaternary_value'])
        else:
            back_camera = 'N/A'

        result['back_camera'] = back_camera

        if elastic_search_result['front_camera_value']:
            front_camera = '{} MP'.format(
                elastic_search_result['front_camera_value'])
            if 'front_camera_secondary_value' in elastic_search_result:
                front_camera += ' + {} MP'.format(
                    elastic_search_result['front_camera_secondary_value'])
        else:
            front_camera = 'N/A'

        result['front_camera'] = front_camera

        return result
    elif m == 'CellPlan':
        result = {
            'main_points': cell_plan_main_points(elastic_search_result),
            'base_name': '{} {}'.format(
                elastic_search_result['line_unicode'],
                elastic_search_result['name'] or '').strip(),
            'brand_unicode': elastic_search_result['line_brand_unicode']
        }
        return result


def unicode_function(im):
    m = im.model.name
    if m == 'Cell':
        result = u'{} {}'.format(im.line, im.name)

        bundle_text = im.bundle.unicode_representation
        if bundle_text.lower() != 'sin bundle':
            result = u'{} + {}'.format(result, bundle_text)

        return result
