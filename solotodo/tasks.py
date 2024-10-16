from celery import shared_task
from django.core.mail import EmailMessage
from django.http import QueryDict

from solotodo.models import Store, Category, StoreUpdateLog, Product, Entity


@shared_task(
    queue="store_update",
    ignore_result=True,
    autoretry_for=(Exception,),
    max_retries=2,
    default_retry_delay=10,
)
def store_update(
    store_id,
    category_ids=None,
    discover_urls_concurrency=None,
    products_for_url_concurrency=None,
    use_async=None,
    update_log_id=None,
    extra_args=None,
):
    store = Store.objects.get(pk=store_id)

    if category_ids:
        categories = Category.objects.filter(pk__in=category_ids)
    else:
        categories = None

    categories = store.sanitize_categories_for_update(categories)

    sanitized_parameters = store.scraper.sanitize_parameters(
        discover_urls_concurrency=discover_urls_concurrency,
        products_for_url_concurrency=products_for_url_concurrency,
        use_async=use_async,
    )

    discover_urls_concurrency = sanitized_parameters["discover_urls_concurrency"]
    products_for_url_concurrency = sanitized_parameters["products_for_url_concurrency"]
    use_async = sanitized_parameters["use_async"]

    if update_log_id:
        update_log = StoreUpdateLog.objects.get(pk=update_log_id)
    else:
        update_log = StoreUpdateLog.objects.create(store=store)

    update_log.discovery_url_concurrency = discover_urls_concurrency
    update_log.products_for_url_concurrency = products_for_url_concurrency
    update_log.use_async = use_async
    update_log.save()

    update_log.categories.set(categories)

    # Reset the categories to synchronize the task signature with the
    # actual method implementation
    if category_ids is None:
        categories = None

    store.update_pricing(
        categories=categories,
        discover_urls_concurrency=discover_urls_concurrency,
        products_for_url_concurrency=products_for_url_concurrency,
        use_async=use_async,
        update_log=update_log,
        extra_args=extra_args,
    )


@shared_task(
    queue="store_update",
    ignore_result=True,
    autoretry_for=(Exception,),
    max_retries=2,
    default_retry_delay=10,
)
def store_update_non_blocker(
    store_id,
    category_ids=None,
    discover_urls_concurrency=None,
    products_for_url_concurrency=None,
    use_async=None,
    update_log_id=None,
    extra_args=None,
):
    store = Store.objects.get(pk=store_id)

    if category_ids:
        categories = Category.objects.filter(pk__in=category_ids)
    else:
        categories = None

    categories = store.sanitize_categories_for_update(categories)

    # TODO update this
    if category_ids and not categories.exists():
        print(f"Categories {category_ids} not found for store {store.name}")
        return

    sanitized_parameters = store.scraper.sanitize_parameters(
        discover_urls_concurrency=discover_urls_concurrency,
        products_for_url_concurrency=products_for_url_concurrency,
        use_async=use_async,
    )
    discover_urls_concurrency = sanitized_parameters["discover_urls_concurrency"]
    products_for_url_concurrency = sanitized_parameters["products_for_url_concurrency"]
    use_async = sanitized_parameters["use_async"]

    if update_log_id:
        update_log = StoreUpdateLog.objects.get(pk=update_log_id)
    else:
        update_log = StoreUpdateLog.objects.create(store=store)

    update_log.discovery_url_concurrency = discover_urls_concurrency
    update_log.products_for_url_concurrency = products_for_url_concurrency
    update_log.use_async = use_async
    update_log.categories.set(categories)
    update_log.save()

    # Reset the categories to synchronize the task signature with the
    # actual method implementation
    if category_ids is None:
        categories = None

    store.update_pricing_non_blocker(
        categories=categories,
        discover_urls_concurrency=discover_urls_concurrency,
        products_for_url_concurrency=products_for_url_concurrency,
        use_async=use_async,
        update_log=update_log,
        extra_args=extra_args,
    )


@shared_task(queue="store_update")
def store_update_pricing_from_json(store_id, json_data):
    store = Store.objects.get(pk=store_id)

    update_log = StoreUpdateLog.objects.create(store=store)

    update_log.categories.set(
        Category.objects.filter(storescraper_name__in=json_data["categories"])
    )

    store.update_pricing_from_json(json_data, update_log=update_log)


@shared_task(queue="general", ignore_result=True)
def product_save(product_id):
    Product.objects.get(pk=product_id).save()


@shared_task(queue="general", ignore_result=True)
def entity_save(entity_id):
    Entity.objects.get(pk=entity_id).save()


@shared_task(queue="general", ignore_result=True)
def es_leads_index():
    from solotodo.models import Lead
    from solotodo.es_models.es_lead import EsLead

    bucket_count = Lead.objects.count() // 5000

    for i in range(bucket_count):
        offset = i * 5000
        print("{} de {}".format(i, bucket_count))

        lead_ids = [
            x["id"] for x in Lead.objects.all()[offset : offset + 5000].values("id")
        ]

        leads = Lead.objects.filter(pk__in=lead_ids)

        EsLead.create_from_db_leads(leads)


@shared_task(queue="general", ignore_result=True)
def entity_save(entity_id):
    Entity.objects.get(pk=entity_id).save()


@shared_task(queue="reports", ignore_result=True, task_time_limit=60 * 30)
def send_historic_entity_positions_report_task(store_id, user_id, query_string):
    from django.contrib.auth import get_user_model
    from solotodo.forms.store_historic_entity_positions_form import (
        StoreHistoricEntityPositionsForm,
    )

    user = get_user_model().objects.get(pk=user_id)
    store = Store.objects.get(pk=store_id)

    q_dict = QueryDict(query_string)
    form = StoreHistoricEntityPositionsForm(user, q_dict)

    if not form.is_valid():
        return

    report_data = form.generate_report(store)
    report_filename = "{}.xlsx".format(report_data["filename"])
    report_file = report_data["file"]

    formatted_start_date = form.cleaned_data["timestamp"].start.strftime("%Y-%m-%d")
    formatted_end_date = form.cleaned_data["timestamp"].stop.strftime("%Y-%m-%d")

    selected_categories = form.cleaned_data["categories"]
    available_categories = form.fields["categories"].queryset

    if len(selected_categories) == len(available_categories):
        formatted_categories = "Todas las categorias"
    else:
        formatted_categories = ", ".join([str(x) for x in selected_categories])

    sender = get_user_model().get_bot().email_recipient_text()
    message = (
        "Se adjunta el reporte de posicionamiento histórico para la "
        "tienda {} entre {} y {} para las categorias: {}"
        "".format(store, formatted_start_date, formatted_end_date, formatted_categories)
    )

    subject = "Reporte posicionamiento histórico {} - {} al {} - {}".format(
        store, formatted_start_date, formatted_end_date, formatted_categories
    )

    email = EmailMessage(subject, message, sender, [user.email])
    email.attach(
        report_filename,
        report_file,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    email.send()


@shared_task(queue="general", ignore_result=True)
def update_entity_sec_qr_codes(entity_id):
    e = Entity.objects.get(pk=entity_id)
    e.update_sec_qr_codes()
