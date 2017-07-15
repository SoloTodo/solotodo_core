import json
import tempfile

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import DefaultStorage
from django.db import models

from solotodo.models.country import Country
from solotodo.models.product_type import ProductType
from solotodo.utils import iterable_to_dict
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
               use_async=None):
        scraper = self.scraper

        # 1. Parameter normalization

        if product_types is None:
            product_types = []

        sanitized_parameters = scraper.sanitize_parameters(
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

        # 2. First pass of product retrieval

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
        scraped_products_data = products_task_signature.delay().get()

        # 3. Second pass of product retrieval, for the products mis-catalogued
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

        extra_scraped_products_data = scraper.products_for_urls(
            extra_entities_args,
            extra_args=extra_args,
            queue=queue,
            products_for_url_concurrency=products_for_url_concurrency,
            use_async=use_async
        )

        scraped_products = [StorescraperProduct.deserialize(p)
                            for p in scraped_products_data['products'] +
                            extra_scraped_products_data['products']]

        discovery_urls_without_products = \
            scraped_products_data['discovery_urls_without_products'] + \
            extra_scraped_products_data['discovery_urls_without_products']

        self.update_with_scraped_products(product_types, scraped_products,
                                          discovery_urls_without_products)

    def update_from_json(self, json_data):
        product_types_dict = iterable_to_dict(ProductType, 'storescraper_name')

        product_types = [product_types_dict[product_type_name]
                         for product_type_name in json_data['product_types']]

        products = [StorescraperProduct.deserialize(product)
                    for product in json_data['products']]

        self.update_with_scraped_products(
            product_types, products,
            json_data['discovery_urls_without_products'])

    def update_with_scraped_products(self, product_types, scraped_products,
                                     discovery_urls_without_products):
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

        # 4. Create log file

        serialized_scraping_info = {
            'product_types': [pt.storescraper_name for pt in product_types],
            'discovery_urls_without_products': discovery_urls_without_products,
            'products': [p.serialize() for p in scraped_products]
        }

        storage = settings.PRIVATE_STORAGE()
        scraping_record_file = ContentFile(json.dumps(
            serialized_scraping_info).encode('utf-8'))
        storage.save('logs/scrapings/{}.json'.format(self),
                     scraping_record_file)

    class Meta:
        ordering = ['name']
        app_label = 'solotodo'
