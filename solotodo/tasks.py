from celery import shared_task

from solotodo.models import Store, ProductType, StoreUpdateLog


@shared_task(queue='store_update')
def store_update(store_id, product_type_ids=None, extra_args=None, queue=None,
                 discover_urls_concurrency=None,
                 products_for_url_concurrency=None,
                 use_async=None):
    store = Store.objects.get(pk=store_id)

    if product_type_ids:
        product_types = ProductType.objects.get(pk__in=product_type_ids)
    else:
        product_types = None

    product_types = store.sanitize_product_types_for_update(product_types)

    sanitized_parameters = store.scraper.sanitize_parameters(
        queue=queue, discover_urls_concurrency=discover_urls_concurrency,
        products_for_url_concurrency=products_for_url_concurrency,
        use_async=use_async)

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

    # Reset the product types to synchronize the task signature with the
    # actual method implementation
    if product_type_ids is None:
        product_types = None

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
