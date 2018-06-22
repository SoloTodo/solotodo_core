import json

from celery.result import allow_join_result
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import Q
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user
from sorl.thumbnail import ImageField

from solotodo.models.utils import rs_refresh_model
from .store_type import StoreType
from .country import Country
from .category import Category
from solotodo.utils import iterable_to_dict
from solotodo_core.s3utils import PrivateS3Boto3Storage
from storescraper.product import Product as StorescraperProduct
from storescraper.utils import get_store_class_by_name


class StoreQuerySet(models.QuerySet):
    def filter_by_user_perms(self, user, permission):
        return get_objects_for_user(user, permission, self)


class Store(models.Model):
    name = models.CharField(max_length=255, db_index=True, unique=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    last_activation = models.DateTimeField(null=True, blank=True)
    storescraper_class = models.CharField(max_length=255, db_index=True)
    storescraper_extra_args = models.CharField(max_length=255, null=True,
                                               blank=True)
    type = models.ForeignKey(StoreType, on_delete=models.CASCADE)
    logo = ImageField(upload_to='store_logos')

    objects = StoreQuerySet.as_manager()

    scraper = property(
        lambda self: get_store_class_by_name(self.storescraper_class))

    def __str__(self):
        return self.name

    def update_pricing(self, categories=None,
                       discover_urls_concurrency=None,
                       products_for_url_concurrency=None,
                       use_async=None, update_log=None):
        assert self.last_activation is not None

        scraper = self.scraper

        categories = self.sanitize_categories_for_update(categories)

        if not categories:
            return

        if update_log:
            update_log.status = update_log.IN_PROCESS
            update_log.save()

        extra_args = {}
        if self.storescraper_extra_args:
            extra_args = json.loads(self.storescraper_extra_args)

        # First pass of product retrieval

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

        try:
            scraped_products_data = scraper.products(
                categories=[c.storescraper_name for c in categories],
                extra_args=extra_args,
                discover_urls_concurrency=discover_urls_concurrency,
                products_for_url_concurrency=products_for_url_concurrency,
                use_async=use_async

            )
        except Exception as e:
            log_update_error(e)
            raise

        # Second pass of product retrieval, for the products mis-catalogued
        # in the store
        extra_entities = self.entity_set.filter(
            category__in=categories
        ).exclude(
            scraped_category__in=categories,
        ).exclude(
            # Exclude the entities that we already scraped previously. This
            # happens when categories is None and is sanitized to include
            # the categories of these entities.
            key__in=[e.key for e in scraped_products_data['products']]
        )

        extra_entities_args = [dict([
            ('url', e.discovery_url),
            ('category', e.scraped_category.storescraper_name)])
            for e in extra_entities]

        extra_products_task_signature = scraper.products_for_urls_task.s(
            self.storescraper_class,
            extra_entities_args,
            extra_args=extra_args,
            products_for_url_concurrency=products_for_url_concurrency,
            use_async=use_async
        )

        extra_products_task_signature.set(queue='storescraper')

        # Prevents Celery error for running a task inside another
        with allow_join_result():
            try:
                extra_products_data = \
                    extra_products_task_signature.delay().get()
            except Exception as e:
                log_update_error(e)
                raise

        scraped_products = scraped_products_data['products'] + \
            extra_products_data['products']

        discovery_urls_without_products = \
            scraped_products_data['discovery_urls_without_products'] + \
            extra_products_data['discovery_urls_without_products']

        self.update_with_scraped_products(categories, scraped_products,
                                          discovery_urls_without_products,
                                          update_log=update_log)

    def update_pricing_from_json(self, json_data, update_log=None):
        assert self.last_activation is not None

        categories = Category.objects.filter(
            storescraper_name__in=json_data['categories'])

        products = [StorescraperProduct.deserialize(product)
                    for product in json_data['products']]

        self.update_with_scraped_products(
            categories, products,
            json_data['discovery_urls_without_products'],
            update_log=update_log
        )

    def update_with_scraped_products(self, categories, scraped_products,
                                     discovery_urls_without_products,
                                     update_log=None):
        from solotodo.models import Currency, Entity

        assert self.last_activation is not None

        scraped_products_dict = iterable_to_dict(scraped_products, 'key')
        entities_to_be_updated = self.entity_set.filter(
            Q(category__in=categories) |
            Q(key__in=scraped_products_dict.keys())).select_related()

        categories_dict = iterable_to_dict(Category, 'storescraper_name')
        currencies_dict = iterable_to_dict(Currency, 'iso_code')

        for entity in entities_to_be_updated:
            scraped_product_for_update = scraped_products_dict.pop(
                entity.key, None)

            if scraped_product_for_update:
                category = categories_dict[
                    scraped_product_for_update.category]
                currency = currencies_dict[
                    scraped_product_for_update.currency]
            else:
                category = None
                currency = None

            entity.update_with_scraped_product(
                scraped_product_for_update,
                category,
                currency)

        for scraped_product in scraped_products_dict.values():
            Entity.create_from_scraped_product(
                scraped_product,
                self,
                categories_dict[scraped_product.category],
                currencies_dict[scraped_product.currency],
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
                'categories': [c.storescraper_name for c in categories],
                'discovery_urls_without_products':
                    discovery_urls_without_products,
                'products': [p.serialize() for p in scraped_products]
            }

            storage = PrivateS3Boto3Storage()
            scraping_record_file = ContentFile(json.dumps(
                serialized_scraping_info, indent=4).encode('utf-8'))

            desired_filename = 'logs/scrapings/{}_{}.json'.format(
                self, timezone.localtime(update_log.creation_date).strftime(
                    '%Y-%m-%d_%X'))
            real_filename = storage.save(desired_filename,
                                         scraping_record_file)
            update_log.registry_file = real_filename

            update_log.save()

    def scraper_categories(self):
        return Category.objects.filter(
            storescraper_name__in=self.scraper.categories())

    def sanitize_categories_for_update(self, original_categories=None):
        sanitized_categories = self.scraper_categories()

        if original_categories:
            sanitized_categories &= original_categories

        # If we have entities whose categories differ between our backend
        # and the store itself add their categories manually to the list of
        # categories to be updated if the original categories are not
        # given
        # Example:
        # 1. "Sanitize all the categories from AbcDin"
        # (original_categories = None)
        # 2. Load the default categories from AbcDin [Television, etc...]
        # 3. We may have an entity from AbcDin with mismatched category.
        # For example they had a Processor in the Notebook section
        # Normally this entity would never be updated as Processor is not
        # part of AbcDin scraper, so add "Processor" to the list of categories
        if original_categories is None:
            extra_category_ids = self.entity_set.exclude(
                category__in=sanitized_categories).values(
                'category')
            extra_categories = Category.objects.filter(
                pk__in=[e['category'] for e in extra_category_ids])
            sanitized_categories |= extra_categories

        return sanitized_categories

    @classmethod
    def rs_refresh(cls):
        rs_refresh_model(cls, 'store', ['id', 'name', 'country_id', 'type_id'])

    class Meta:
        app_label = 'solotodo'
        ordering = ['name']
        permissions = (
            ['view_store', 'Can view the store'],
            ['view_store_update_logs', 'Can view the store update logs'],
            ['view_store_stocks', 'Can view the store entities stock'],
            ['update_store_pricing', 'Can update the store pricing'],
            ['view_store_leads', 'View the leads associated to this store'],
            ['view_store_reports',
             'Download the reports associated to this store'],
            # "Backend" permissions are used exclusively for UI purposes, they
            # are not used at the API level
            ['backend_list_stores', 'Can view store list in backend'],
        )
