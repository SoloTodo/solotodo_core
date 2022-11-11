from decimal import Decimal


def pretty_cell_battery(cell):
    if cell['battery_mah']:
        result = '{} mAh'.format(cell['battery_mah'])
    else:
        result = 'N/A'

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


def additional_es_fields(elastic_search_result, model_name):
    m = model_name

    if m == 'Cell':
        result = {
            'pretty_battery': pretty_cell_battery(elastic_search_result),
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

        result['base_model_internal_storage_ram_key'] = \
            elastic_search_result['base_model_id'] + \
            100 * elastic_search_result['internal_storage_id'] + \
            1000 * elastic_search_result['ram_id']
        result['default_bucket'] = \
            result['base_model_internal_storage_ram_key']

        result['storage_and_ram'] = '{} / {}'.format(
            elastic_search_result['internal_storage_unicode'],
            elastic_search_result['ram_unicode'],
        )

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
            if 'back_camera_quinary_value' in elastic_search_result:
                back_camera += ' + {} MP'.format(
                    elastic_search_result['back_camera_quinary_value'])
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

        # General score computation

        scores = []

        # Maxes based on current Snapdragon 855 scores (March 2020)
        score_fields = [
            ('geekbench_44_single_core_score', 3500),
            ('geekbench_44_multi_core_score', 11000),
            ('geekbench_5_single_core_score', 750),
            ('geekbench_5_multi_core_score', 2600),
            ('passmark_score', 500000),
        ]

        for score_field, max_score in score_fields:
            field_name = 'soc_' + score_field

            if not elastic_search_result.get(field_name):
                continue

            relative_score = int(
                1000 * elastic_search_result.get(field_name, 0) / max_score)

            if relative_score > 1000:
                relative_score = 1000

            scores.append(relative_score)

        if scores:
            general_score = int(sum(scores) / len(scores))
        else:
            general_score = 0

        tags = []
        if elastic_search_result['network_generation_unicode'] == '5G':
            tags.append('5G')

        result['tags'] = tags

        warnings = []

        if elastic_search_result['operating_system_line_is_discontinued']:
            warnings.append('El sistema operativo con el que este celular '
                            'fue lanzado está descontinuado. Por favor '
                            'verifique si es que tiene disponible una '
                            'actualización de software reciente antes '
                            'de comprarlo')

        if elastic_search_result['line_brand_unicode'] == 'Huawei':
            warnings.append('Los smartphones Huawei no tienen disponibles las '
                            'aplicaciones de Google (Youtube, GMail, etc) '
                            'ni acceso a la Play Store.')
        if elastic_search_result['operating_system_line_unicode'] == \
                'Google Android Go':
            warnings.append('Este equipo viene con Android "Go" como sistema '
                            'operativo, que es más básico y limitado que '
                            'Android tradicional')
        if elastic_search_result['category_unicode'] == 'Smartphone' and elastic_search_result['ram_value'] < 4096:
            warnings.append('Este equipo solo tiene {} de RAM. SoloTodo '
                            'recomienda equipos con por lo menos 4 GB de RAM '
                            'para un celular actual.'.format(
                elastic_search_result['ram_unicode']))
        if elastic_search_result['category_unicode'] == 'Smartphone' and elastic_search_result['internal_storage_value'] < 65536:
            warnings.append('Este equipo solo tiene {} de memoria. SoloTodo '
                            'recomienda equipos con por lo menos 64 GB de '
                            'almacenamiento para un celular actual.'.format(
                elastic_search_result['internal_storage_unicode']))

        result['warnings'] = warnings

        result['general_score'] = general_score

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
