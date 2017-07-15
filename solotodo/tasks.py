from celery import shared_task

from solotodo.models import Store, ProductType, StoreUpdateLog


@shared_task(queue='store_update')
def store_update(store_id, product_type_ids=None, extra_args=None, queue=None,
                 discover_urls_concurrency=None,
                 products_for_url_concurrency=None,
                 use_async=None):
    store = Store.objects.get(pk=store_id)
    scraper = store.scraper

    product_types = ProductType.objects.filter(
        storescraper_name__in=scraper.product_types())

    if product_type_ids is not None:
        product_types = product_types.filter(
            pk__in=product_type_ids
        )

    sanitized_parameters = store.scraper.sanitize_parameters(
        product_types=[pt.storescraper_name for pt in product_types],
        queue=queue, discover_urls_concurrency=discover_urls_concurrency,
        products_for_url_concurrency=products_for_url_concurrency,
        use_async=use_async)

    product_types = ProductType.objects.filter(
        storescraper_name__in=sanitized_parameters['product_types'])
    queue = sanitized_parameters['queue']
    discover_urls_concurrency = \
        sanitized_parameters['discover_urls_concurrency']
    products_for_url_concurrency = \
        sanitized_parameters['products_for_url_concurrency']
    use_async = sanitized_parameters['use_async']

    update_log = StoreUpdateLog.objects.create(
        store=store,
        discovery_url_concurrency=discover_urls_concurrency,
        products_for_url_concurrency=products_for_url_concurrency,
        use_async=use_async,
        queue=queue
    )

    update_log.product_types = product_types

    store.update(product_types=product_types, extra_args=extra_args,
                 queue=queue,
                 discover_urls_concurrency=discover_urls_concurrency,
                 products_for_url_concurrency=products_for_url_concurrency,
                 use_async=use_async, update_log=update_log)


@shared_task(queue='store_update')
def store_update_from_json(store_id, json_data):
    store = Store.objects.get(pk=store_id)

    update_log = StoreUpdateLog.objects.create(
        store=store
    )

    update_log.product_types = ProductType.objects.filter(
        storescraper_name__in=json_data['product_types'])

    store.update_from_json(json_data, update_log=update_log)
