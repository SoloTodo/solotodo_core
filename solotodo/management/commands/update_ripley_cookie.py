import json
import time

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management import BaseCommand

from solotodo.models import Store
from storescraper.utils import HeadlessChrome, CF_REQUEST_HEADERS


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--stores', nargs='*', type=str)

    def handle(self, *args, **options):
        ac_settings = settings.ANTICAPTCHA

        proxy = 'http://{}:{}@{}:{}'.format(
            ac_settings['PROXY_USERNAME'],
            ac_settings['PROXY_PASSWORD'],
            ac_settings['PROXY_IP'],
            ac_settings['PROXY_PORT'],
        )
        with HeadlessChrome(images_enabled=True, proxy=proxy,
                            headless=True) as driver:
            driver.get('https://simple.ripley.cl')
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            hcaptcha_script_tag = soup.find('script', {'data-type': 'normal'})
            website_key = hcaptcha_script_tag['data-sitekey']

            # Anti captcha request
            request_body = {
                "clientKey": ac_settings['KEY'],
                "task":
                    {
                        "type": "HCaptchaTask",
                        "websiteURL": "https://simple.ripley.cl/",
                        "websiteKey": website_key,
                        "proxyType": "http",
                        "proxyAddress": ac_settings['PROXY_IP'],
                        "proxyPort": ac_settings['PROXY_PORT'],
                        "proxyLogin": ac_settings['PROXY_USERNAME'],
                        "proxyPassword": ac_settings['PROXY_PASSWORD'],
                        "userAgent": CF_REQUEST_HEADERS['User-Agent']
                    }
            }
            print('Sending anti-captcha task')
            print(json.dumps(request_body, indent=2))
            anticaptcha_session = requests.Session()
            anticaptcha_session.headers['Content-Type'] = 'application/json'
            response = json.loads(anticaptcha_session.post(
                'http://api.anti-captcha.com/createTask',
                json=request_body).text)

            print('Anti-captcha task request response')
            print(json.dumps(response, indent=2))

            assert response['errorId'] == 0

            task_id = response['taskId']
            print('TaskId', task_id)

            # Wait until the task is ready...
            get_task_result_params = {
                "clientKey": ac_settings['KEY'],
                "taskId": task_id
            }
            print(
                'Querying for anti-captcha response (wait 10 secs per retry)')
            print(json.dumps(get_task_result_params, indent=4))
            retries = 1
            hcaptcha_response = None
            while not hcaptcha_response:
                if retries > 60:
                    raise Exception('Failed to get a token in time')
                print('Retry #{}'.format(retries))
                time.sleep(10)
                res = json.loads(anticaptcha_session.post(
                    'https://api.anti-captcha.com/getTaskResult',
                    json=get_task_result_params).text)

                assert res['errorId'] == 0, res
                assert res['status'] in ['processing', 'ready'], res
                if res['status'] == 'ready':
                    print('Solution found')
                    hcaptcha_response = res['solution']['gRecaptchaResponse']
                    break
                retries += 1

            print(hcaptcha_response)
            for field in ['g-recaptcha-response', 'h-captcha-response']:
                driver.execute_script("document.querySelector('[name=\""
                                      "{0}\"]').remove(); "
                                      "var foo = document.createElement('"
                                      "input'); foo.setAttribute('name', "
                                      "'{0}'); "
                                      "foo.setAttribute('value','{1}'); "
                                      "document.getElementsByTagName('form')"
                                      "[0].appendChild(foo);".format(
                                        field, hcaptcha_response))
            driver.execute_script("document.getElementsByTagName('form')"
                                  "[0].submit()")

            d = {
                "proxy": proxy,
                "cf_clearance": driver.get_cookie('cf_clearance')['value'],
                "__cfduid": driver.get_cookie('__cfduid')['value']
            }
            print(json.dumps(d, indent=2))
            store = Store.objects.get(pk=settings.RIPLEY_STORE_ID)
            store.storescraper_extra_args = json.dumps(d)
            store.save()
