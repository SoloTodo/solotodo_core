import json

from celery.result import allow_join_result
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone

from solotodo.models.country import Country
from solotodo.models.product_type import ProductType
from solotodo.utils import iterable_to_dict
from solotodo_try.s3utils import PrivateS3Boto3Storage
from storescraper.product import Product as StorescraperProduct
from storescraper.utils import get_store_class_by_name


class Store(models.Model):
    name = models.CharField(max_length=255, db_index=True, unique=True)
    country = models.ForeignKey(Country)
    is_active = models.BooleanField(default=True)
    storescraper_class = models.CharField(max_length=255, db_index=True)
    storescraper_extra_args = models.CharField(max_length=255, null=True,
                                               blank=True)

    scraper = property(
        lambda self: get_store_class_by_name(self.storescraper_class))

    def __str__(self):
        return self.name

    def update(self, product_types=None, extra_args=None, queue=None,
               discover_urls_concurrency=None,
               products_for_url_concurrency=None,
               use_async=None, update_log=None):
        scraper = self.scraper

        if product_types is not None:
            product_types = product_types.filter(
                storescraper_name__in=scraper.product_types())
        else:
            product_types = ProductType.objects.filter(
                storescraper_name__in=scraper.product_types())

        if update_log:
            update_log.status = update_log.IN_PROCESS
            update_log.save()

        # First pass of product retrieval

        products_task_signature = scraper.products_task.s(
            self.storescraper_class,
            product_types=[pt.storescraper_name for pt in product_types],
            extra_args=extra_args,
            queue=queue,
            discover_urls_concurrency=discover_urls_concurrency,
            products_for_url_concurrency=products_for_url_concurrency,
            use_async=use_async
        )

        products_task_signature.set(queue='storescraper_api_' + queue)

        def log_update_error(exception):
            if update_log:
                update_log.status = update_log.ERROR
                desired_filename = 'logs/scrapings/{}_{}.json'.format(
                    self, timezone.localtime(
                        update_log.creation_date).strftime('%Y-%m-%d_%X'))
                storage = PrivateS3Boto3Storage()
                real_filename = storage.save(
                    desired_filename, ContentFile(
                        str(exception).encode('utf-8')))
                update_log.registry_file = real_filename
                update_log.save()

        # Prevents Celery error for running a task inside another
        with allow_join_result():
            try:
                scraped_products_data = products_task_signature.delay().get()
            except Exception as e:
                log_update_error(e)
                raise

        # Second pass of product retrieval, for the products mis-catalogued
        # in the store
        extra_entities = self.entity_set.filter(
            product_type__in=product_types
        ).exclude(
            scraped_product_type__in=product_types
        )

        extra_entities_args = [dict([
            ('url', e.discovery_url),
            ('product_type', e.scraped_product_type.storescraper_name)])
            for e in extra_entities]

        extra_products_task_signature = scraper.products_for_urls_task.s(
            self.storescraper_class,
            extra_entities_args,
            extra_args=extra_args,
            queue=queue,
            products_for_url_concurrency=products_for_url_concurrency,
            use_async=use_async
        )

        extra_products_task_signature.set(queue='storescraper_api_' + queue)

        # Prevents Celery error for running a task inside another
        with allow_join_result():
            try:
                extra_products_data = \
                    extra_products_task_signature.delay().get()
            except Exception as e:
                log_update_error(e)
                raise

        scraped_products = [StorescraperProduct.deserialize(p)
                            for p in scraped_products_data['products'] +
                            extra_products_data['products']]

        discovery_urls_without_products = \
            scraped_products_data['discovery_urls_without_products'] + \
            extra_products_data['discovery_urls_without_products']

        self.update_with_scraped_products(product_types, scraped_products,
                                          discovery_urls_without_products,
                                          update_log=update_log)

    def update_from_json(self, json_data, update_log=None):
        product_types = ProductType.objects.filter(
            storescraper_name__in=json_data['product_types'])

        products = [StorescraperProduct.deserialize(product)
                    for product in json_data['products']]

        self.update_with_scraped_products(
            product_types, products,
            json_data['discovery_urls_without_products'],
            update_log=update_log
        )

    def update_with_scraped_products(self, product_types, scraped_products,
                                     discovery_urls_without_products,
                                     update_log=None):
        from solotodo.models import Currency, Entity

        scraped_products_dict = iterable_to_dict(scraped_products, 'key')
        entities_to_be_updated = self.entity_set.filter(
            product_type__in=product_types).select_related()

        product_types_dict = iterable_to_dict(ProductType, 'storescraper_name')
        currencies_dict = iterable_to_dict(Currency, 'iso_code')

        for entity in entities_to_be_updated:
            scraped_product_for_update = scraped_products_dict.pop(
                entity.key, None)

            if scraped_product_for_update:
                product_type = product_types_dict[
                    scraped_product_for_update.product_type]
                currency = currencies_dict[
                    scraped_product_for_update.currency]
            else:
                product_type = None
                currency = None

            entity.update_with_scraped_product(
                scraped_product_for_update,
                product_type,
                currency)

        for scraped_product in scraped_products_dict.values():
            Entity.create_from_scraped_product(
                scraped_product,
                self,
                product_types_dict[scraped_product.product_type],
                currencies_dict[scraped_product.currency]
            )

        if update_log:
            update_log.status = update_log.SUCCESS
            update_log.available_products_count = len(
                list(filter(lambda x: x.is_available(), scraped_products)))
            update_log.unavailable_products_count = len(
                list(filter(lambda x: not x.is_available(), scraped_products)))
            update_log.discovery_urls_without_products_count = len(
                discovery_urls_without_products)

            serialized_scraping_info = {
                'product_types': [pt.storescraper_name
                                  for pt in product_types],
                'discovery_urls_without_products':
                    discovery_urls_without_products,
                'products': [p.serialize() for p in scraped_products]
            }

            storage = PrivateS3Boto3Storage()
            scraping_record_file = ContentFile(json.dumps(
                serialized_scraping_info).encode('utf-8'))

            desired_filename = 'logs/scrapings/{}_{}.json'.format(
                self, timezone.localtime(update_log.creation_date).strftime(
                    '%Y-%m-%d_%X'))
            real_filename = storage.save(desired_filename,
                                         scraping_record_file)
            update_log.registry_file = real_filename

            update_log.save()

    class Meta:
        ordering = ['name']
        app_label = 'solotodo'
