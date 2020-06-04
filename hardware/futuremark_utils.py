# Retrieves scores from FutureMark
import json
import requests


def get_futuremark_score(futuremark_id, component_code, test_id, test_mode):
    session = requests.Session()

    if futuremark_id == '0':
        return 0
    base_url = 'https://www.3dmark.com'
    args = '?minScore=1'

    page_url = base_url + '/proxycon/ajax/search/%s/%s/%s/%s/2147483647/%s' %\
        (component_code, test_id, test_mode, futuremark_id, args)

    scores = []
    while True:
        print(page_url)
        data = session.get(page_url).text
        json_data = json.loads(data)
        for result in json_data['results']:
            if result['gpuCount'] > 1:
                continue
            scores.append(result['overallScore'])

        try:
            next_page_url = json_data['nextPageLink']
        except KeyError:
            break

        if not next_page_url:
            break

        page_url = base_url + next_page_url + args

    if not scores:
        return 0

    return sum(scores) // len(scores)


def get_tdmark_11_score(tdmark_id):
    return _get_tdmark_score(tdmark_id, '3dm11', 'P')


def get_tdmark_cloud_gate_score(tdmark_id):
    return _get_tdmark_score(tdmark_id, 'cg', 'P')


def get_tdmark_fire_strike_score(tdmark_id):
    return _get_tdmark_score(tdmark_id, 'fs', 'P')


def _get_tdmark_score(tdmark_id, test_id, test_mode):
    return get_futuremark_score(
        tdmark_id, 'gpu', test_id, test_mode)
