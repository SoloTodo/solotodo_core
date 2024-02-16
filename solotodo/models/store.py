import json
import io
import base64
import traceback

import xlsxwriter
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import Q
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user, get_objects_for_group
from sorl.thumbnail import ImageField

from .store_type import StoreType
from .country import Country
from .category import Category
from solotodo.utils import iterable_to_dict, validate_sii_rut
from solotodo_core.s3utils import PrivateS3Boto3Storage, MediaRootS3Boto3Storage
from storescraper.product import Product as StorescraperProduct
from storescraper.utils import get_store_class_by_name


class StoreQuerySet(models.QuerySet):
    def filter_by_user_perms(self, user, permission, reload_cache=False):
        from solotodo_core import settings

        if user.is_superuser:
            return self

        user_group_names = [x["name"] for x in user.groups.values("name")]

        if permission == "view_store" and (
            user.is_anonymous or user_group_names == [settings.DEFAULT_GROUP_NAME]
        ):
            return self.filter_viewable_by_default_group(reload_cache=reload_cache)

        return get_objects_for_user(user, permission, self)

    def filter_by_banners_support(self):
        stores_with_banner_compatibility = []
        for store in self:
            try:
                _ = store.scraper.banners
                stores_with_banner_compatibility.append(store)
            except AttributeError:
                # The scraper of the store does not implement banners method
                pass

        return self.filter(pk__in=[s.id for s in stores_with_banner_compatibility])

    def filter_viewable_by_default_group(self, reload_cache=False):
        from solotodo_core import settings

        store_ids = cache.get("default_group_store_ids")
        if not store_ids or reload_cache:
            group = Group.objects.get(name=settings.DEFAULT_GROUP_NAME)
            stores = get_objects_for_group(group, "view_store", Store)
            store_ids = [x.id for x in stores]
            cache.set("default_group_store_ids", store_ids)

        return self.filter(pk__in=store_ids)


class Store(models.Model):
    name = models.CharField(max_length=255, db_index=True, unique=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    last_activation = models.DateTimeField(null=True, blank=True)
    storescraper_class = models.CharField(max_length=255, db_index=True)
    storescraper_extra_args = models.CharField(max_length=255, null=True, blank=True)
    type = models.ForeignKey(StoreType, on_delete=models.CASCADE)
    logo = ImageField(upload_to="store_logos")
    preferred_payment_method = models.CharField(null=True, blank=True, max_length=100)
    active_banner_update = models.OneToOneField(
        "banners.BannerUpdate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    group = models.OneToOneField(
        Group,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="preferred_store",
    )
    last_updated = models.DateTimeField(auto_now=True)
    sii_rut = models.CharField(
        max_length=10, null=True, blank=True, validators=[validate_sii_rut]
    )
    sii_razon_social = models.CharField(max_length=255, null=True, blank=True)

    objects = StoreQuerySet.as_manager()

    scraper = property(lambda self: get_store_class_by_name(self.storescraper_class))

    def __str__(self):
        return self.name

    def update_pricing(
        self,
        categories=None,
        discover_urls_concurrency=None,
        products_for_url_concurrency=None,
        use_async=None,
        update_log=None,
        extra_args=None,
    ):
        assert self.last_activation is not None

        scraper = self.scraper

        categories = self.sanitize_categories_for_update(categories)

        if not categories:
            return

        if update_log:
            update_log.status = update_log.IN_PROCESS
            update_log.save()

        local_extra_args = {}

        if self.storescraper_extra_args:
            local_extra_args = json.loads(self.storescraper_extra_args)
        if extra_args:
            local_extra_args.update(extra_args)

        def log_update_error(local_error_message):
            if update_log:
                update_log.status = update_log.ERROR
                desired_filename = "logs/scrapings/{}_{}.json".format(
                    self,
                    timezone.localtime(update_log.creation_date).strftime(
                        "%Y-%m-%d_%X"
                    ),
                )
                storage = PrivateS3Boto3Storage()
                real_filename = storage.save(
                    desired_filename, ContentFile(local_error_message.encode("utf-8"))
                )
                update_log.registry_file = real_filename
                update_log.save()

        print("Scraping products")

        try:
            scraped_products_data = scraper.products(
                categories=[c.storescraper_name for c in categories],
                extra_args=extra_args,
                discover_urls_concurrency=discover_urls_concurrency,
                products_for_url_concurrency=products_for_url_concurrency,
                use_async=use_async,
            )
        except Exception as e:
            error_message = "Unknown error: {}".format(traceback.format_exc())
            log_update_error(error_message)
            raise

        print("Products scraped")

        self.update_with_scraped_products(
            categories,
            scraped_products_data["products"],
            scraped_products_data["discovery_urls_without_products"],
            update_log=update_log,
        )

    def update_pricing_from_json(self, json_data, update_log=None):
        assert self.last_activation is not None

        categories = Category.objects.filter(
            storescraper_name__in=json_data["categories"]
        )

        products = [
            StorescraperProduct.deserialize(product)
            for product in json_data["products"]
        ]

        self.update_with_scraped_products(
            categories,
            products,
            json_data["discovery_urls_without_products"],
            update_log=update_log,
        )

    def update_with_scraped_products(
        self,
        categories,
        scraped_products,
        discovery_urls_without_products,
        update_log=None,
    ):
        from solotodo.models import Currency, Entity

        assert self.last_activation is not None

        print("1")
        scraped_products_dict = iterable_to_dict(scraped_products, "key")
        print("2")
        entities_to_be_updated = self.entity_set.filter(
            Q(category__in=categories) | Q(key__in=scraped_products_dict.keys())
        ).select_related()
        print("3")

        categories_dict = iterable_to_dict(Category, "storescraper_name")
        currencies_dict = iterable_to_dict(Currency, "iso_code")
        sections_dict = iterable_to_dict(self.sections.all(), "name")

        print("4")

        for entity in entities_to_be_updated:
            print(entity.id)
            scraped_product_for_update = scraped_products_dict.pop(entity.key, None)

            if not entity.active_registry_id and not scraped_product_for_update:
                print("skipping")
                continue

            if scraped_product_for_update:
                category = categories_dict[scraped_product_for_update.category]
                currency = currencies_dict[scraped_product_for_update.currency]
            else:
                category = None
                currency = None

            entity.update_with_scraped_product(
                scraped_product_for_update, sections_dict, category, currency
            )

        for scraped_product in scraped_products_dict.values():
            print(scraped_product.key)
            Entity.create_from_scraped_product(
                scraped_product,
                self,
                categories_dict[scraped_product.category],
                currencies_dict[scraped_product.currency],
                sections_dict,
            )

        print("Done")

        if update_log:
            update_log.status = update_log.SUCCESS
            update_log.available_products_count = len(
                list(filter(lambda x: x.is_available(), scraped_products))
            )
            update_log.unavailable_products_count = len(
                list(filter(lambda x: not x.is_available(), scraped_products))
            )
            update_log.discovery_urls_without_products_count = len(
                discovery_urls_without_products
            )

            serialized_scraping_info = {
                "categories": [c.storescraper_name for c in categories],
                "discovery_urls_without_products": discovery_urls_without_products,
                "products": [p.serialize() for p in scraped_products],
            }

            storage = PrivateS3Boto3Storage()
            scraping_record_file = ContentFile(
                json.dumps(serialized_scraping_info, indent=4).encode("utf-8")
            )

            desired_filename = "logs/scrapings/{}_{}.json".format(
                self,
                timezone.localtime(update_log.creation_date).strftime("%Y-%m-%d_%X"),
            )
            real_filename = storage.save(desired_filename, scraping_record_file)
            update_log.registry_file = real_filename

            update_log.save()

    def scraper_categories(self):
        return Category.objects.filter(storescraper_name__in=self.scraper.categories())

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
                category__in=sanitized_categories
            ).values("category")
            extra_categories = Category.objects.filter(
                pk__in=[e["category"] for e in extra_category_ids]
            )
            sanitized_categories |= extra_categories

        return sanitized_categories

    def check_and_fill_active_registries(self):
        from solotodo.models import Entity, EntityHistory, StoreUpdateLog

        success = 3
        today = timezone.now().date()

        logs = StoreUpdateLog.objects.filter(
            store=self, creation_date__date=today, status=success
        )

        if logs:
            return

        entities = Entity.objects.filter(store=self, active_registry__isnull=False)

        for entity in entities:
            current_eh = entity.active_registry

            new_eh = EntityHistory.objects.create(
                entity=entity,
                timestamp=timezone.now(),
                stock=current_eh.stock,
                normal_price=current_eh.normal_price,
                offer_price=current_eh.offer_price,
                cell_monthly_payment=current_eh.cell_monthly_payment,
                picture_count=current_eh.picture_count,
                video_count=current_eh.video_count,
                review_count=current_eh.review_count,
                review_avg_score=current_eh.review_avg_score,
            )

            entity.active_registry = new_eh
            entity.save()

    def update_banners(self):
        from banners.models import (
            BannerUpdate,
            Banner,
            BannerAsset,
            BannerSection,
            BannerSubsection,
            BannerSubsectionType,
        )

        scraper = self.scraper

        if self.storescraper_extra_args:
            extra_args = json.loads(self.storescraper_extra_args)
        else:
            extra_args = {}

        update = BannerUpdate.objects.create(store=self)

        try:
            scraped_banners_data = scraper.banners(extra_args=extra_args)
        except Exception as e:
            update.status = BannerUpdate.ERROR
            update.status_message = str(e)
            update.save()
            return

        section_dict = {
            section.name: section for section in BannerSection.objects.all()
        }

        subsection_type_dict = {
            subsection_type.storescraper_name: subsection_type
            for subsection_type in BannerSubsectionType.objects.all()
        }

        for banner_data in scraped_banners_data:
            if banner_data["section"] not in section_dict:
                update.status = BannerUpdate.ERROR
                update.status_message = "Invalid Section {}".format(
                    banner_data["section"]
                )
                update.save()
                return

            if banner_data["type"] not in subsection_type_dict:
                update.status = BannerUpdate.ERROR
                update.status_message = "Invalid Subsection Type {}".format(
                    banner_data["type"]
                )
                update.save()
                return

        for banner_data in scraped_banners_data:
            try:
                asset = BannerAsset.objects.get(key=banner_data["key"])
            except BannerAsset.DoesNotExist:
                if "picture_url" in banner_data:
                    picture_url = banner_data["picture_url"]
                else:
                    storage = MediaRootS3Boto3Storage()
                    image = base64.b64decode(banner_data["picture"])
                    file = io.BytesIO(image)
                    file.seek(0)
                    file_value = file.getvalue()
                    file_for_upload = ContentFile(file_value)

                    filename_template = "banner_%Y-%m-%d_%H:%M:%S"
                    filename = timezone.now().strftime(filename_template)

                    path = storage.save(
                        "banners/{}.png".format(filename), file_for_upload
                    )
                    picture_url = storage.url(path)

                asset = BannerAsset.objects.create(
                    key=banner_data["key"], picture_url=picture_url
                )

            section = section_dict[banner_data["section"]]
            subsection_type = subsection_type_dict[banner_data["type"]]

            subsection = BannerSubsection.objects.get_or_create(
                name=banner_data["subsection"], section=section, type=subsection_type
            )[0]

            destination_urls = ", ".join(banner_data["destination_urls"])

            Banner.objects.create(
                update=update,
                url=banner_data["url"],
                destination_urls=destination_urls,
                asset=asset,
                subsection=subsection,
                position=banner_data["position"],
            )

        update.status = BannerUpdate.SUCCESS
        update.save()
        self.active_banner_update = update
        self.save()

    def matching_report(self, store):
        from .entity import Entity

        entities = (
            Entity.objects.select_related(
                "active_registry", "product__instance_model", "category"
            )
            .filter(store=store, is_visible=True)
            .get_available()
        )
        output = io.BytesIO()

        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        header_format_left = workbook.add_format(
            {"bold": True, "font_size": 10, "align": "left", "valign": "left"}
        )
        header_format_right = workbook.add_format(
            {"bold": True, "font_size": 10, "align": "right", "valign": "right"}
        )

        worksheet = workbook.add_worksheet()
        headers = [
            "Identificador",
            "SKU",
            "Nombre",
            "Condición",
            "URL",
            "Precio Normal",
            "Precio Oferta",
            "ID SKU SoloTodo",
            "Categoría SoloTodo",
            "Producto SoloTodo",
            "URL SoloTodo",
            "ID Producto SoloTodo",
        ]
        for idx, header in enumerate(headers):
            if "Precio" in header:
                worksheet.write(0, idx, header, header_format_right)
            else:
                worksheet.write(0, idx, header, header_format_left)
        row = 1
        for entity in entities:
            col = 0
            worksheet.write(row, col, entity.key)
            col += 1
            sku = entity.sku or "N/A"
            worksheet.write(row, col, sku)
            col += 1
            worksheet.write(row, col, entity.name)
            col += 1
            worksheet.write(row, col, entity.condition_as_text)
            col += 1
            worksheet.write(row, col, entity.url)
            col += 1
            worksheet.write(row, col, entity.active_registry.normal_price)
            col += 1
            worksheet.write(row, col, entity.active_registry.offer_price)
            col += 1
            worksheet.write(row, col, entity.id)
            col += 1
            worksheet.write(row, col, entity.category.name)
            col += 1
            if entity.product:
                worksheet.write(row, col, entity.product.instance_model.unicode_value)
                col += 1
                worksheet.write(
                    row,
                    col,
                    "https://www.solotodo.cl/products/" + str(entity.product.id),
                )
                col += 1
                worksheet.write(row, col, entity.product_id)
            else:
                worksheet.write(row, col, "N/A")
                col += 1
                worksheet.write(row, col, "N/A")
                col += 1
                worksheet.write(row, col, "N/A")
            row += 1

        workbook.close()
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)
        return file_for_upload

    class Meta:
        app_label = "solotodo"
        ordering = ["name"]
        permissions = (
            ["view_store_update_logs", "Can view the store update logs"],
            ["view_store_stocks", "Can view the store entities stock"],
            ["update_store_pricing", "Can update the store pricing"],
            ["view_store_leads", "View the leads associated to this store"],
            ["view_store_reports", "Download the reports associated to this store"],
            # "Backend" permissions are used exclusively for UI purposes, they
            # are not used at the API level
            ["backend_list_stores", "Can view store list in backend"],
            ["view_store_banners", "Can view store banners"],
            ["view_store_entity_positions", "Can view store entity positions"],
            [
                "create_store_keyword_search",
                "Can create keyword searches in this store",
            ],
            ["view_store_sii_details", "Can view the SII details for the store"],
        )
