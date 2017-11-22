import json

from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user

from solotodo.models import Store, Product, Category
from solotodo.utils import iterable_to_dict
from solotodo_try.s3utils import PrivateS3Boto3Storage
from storescraper.utils import get_store_class_by_name


class WtbBrandQuerySet(models.QuerySet):
    def filter_by_user_perms(self, user, permission):
        return get_objects_for_user(user, permission, self)


class WtbBrand(models.Model):
    name = models.CharField(max_length=100)
    prefered_brand = models.CharField(max_length=100, blank=True, null=True)
    storescraper_class = models.CharField(max_length=100, blank=True,
                                          null=True)
    stores = models.ManyToManyField(Store)

    objects = WtbBrandQuerySet.as_manager()

    scraper = property(
        lambda self: get_store_class_by_name(self.storescraper_class))

    def __str__(self):
        return self.name

    def update_pricing(self,
                       discover_urls_concurrency=None,
                       products_for_url_concurrency=None,
                       use_async=None, update_log=None):
        assert self.storescraper_class

        scraper = self.scraper

        if update_log:
            update_log.status = update_log.IN_PROCESS
            update_log.save()

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
                discover_urls_concurrency=discover_urls_concurrency,
                products_for_url_concurrency=products_for_url_concurrency,
                use_async=use_async
            )
        except Exception as e:
            log_update_error(e)
            raise

        # self.update_with_scraped_products(scraped_products_data['products'],
        #                                   update_log=update_log)

        scraped_products = scraped_products_data['products']
        scraped_products_dict = iterable_to_dict(scraped_products, 'key')

        entities_to_be_updated = self.wtbentity_set.select_related()

        categories_dict = iterable_to_dict(Category, 'storescraper_name')

        for entity in entities_to_be_updated:
            scraped_product_for_update = scraped_products_dict.pop(
                entity.key, None)

            entity.update_with_scraped_product(
                scraped_product_for_update)

        for scraped_product in scraped_products_dict.values():
            WtbEntity.create_from_scraped_product(
                scraped_product,
                self,
                categories_dict[scraped_product.category]
            )

        if update_log:
            update_log.status = update_log.SUCCESS

            serialized_scraping_info = [p.serialize()
                                        for p in scraped_products]

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

    class Meta:
        ordering = ('name', )
        permissions = [
            ('view_wtb_brand', 'Can view the WTB brand'),
            ('backend_view_wtb', 'Display the WTB menu in the backend'),
        ]


class WtbEntity(models.Model):
    name = models.CharField(max_length=255)
    brand = models.ForeignKey(WtbBrand)
    category = models.ForeignKey(Category)
    product = models.ForeignKey(Product, blank=True, null=True)
    key = models.CharField(max_length=255)
    url = models.URLField()
    picture_url = models.URLField()
    creation_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_visible = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return '{} - {}'.format(self.brand, self.name)

    def update_with_scraped_product(self, scraped_product):
        assert scraped_product is None or self.key == scraped_product.key

        if scraped_product:
            self.name = scraped_product.name[:254]
            self.url = scraped_product.url
            self.picture_url = scraped_product.picture_urls[0]
            self.is_active = True
            self.save()
        elif self.is_active:
            self.is_active = False
            self.save()

    @classmethod
    def create_from_scraped_product(cls, scraped_product, brand, category):
        cls.objects.create(
            name=scraped_product.name[:254],
            brand=brand,
            category=category,
            key=scraped_product.key,
            url=scraped_product.url,
            picture_url=scraped_product.picture_urls[0],
        )

    class Meta:
        ordering = ('brand', 'name')


class WtbBrandUpdateLog(models.Model):
    PENDING, IN_PROCESS, SUCCESS, ERROR = [1, 2, 3, 4]

    brand = models.ForeignKey(WtbBrand)
    status = models.IntegerField(choices=[
        (PENDING, 'Pending'),
        (IN_PROCESS, 'In process'),
        (SUCCESS, 'Success'),
        (ERROR, 'Error'),
    ], default=PENDING)
    creation_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    registry_file = models.FileField(storage=PrivateS3Boto3Storage(),
                                     upload_to='logs/wtb',
                                     null=True, blank=True)

    entity_count = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return '{} - {}'.format(self.brand, self.last_updated)

    class Meta:
        ordering = ('brand', '-last_updated')
