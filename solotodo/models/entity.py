import io
import json
import re
import urllib

from decimal import Decimal

from storescraper.utils import session_with_proxy
from PIL import Image
from django.core.validators import validate_comma_separated_integer_list
from pyzbar.pyzbar import decode
from django.contrib.auth import get_user_model
from django.db import models, IntegrityError
from django.db.models import Q, Count
from django.utils import timezone
from solotodo.utils import iterable_to_dict, fetch_sec_fields
from .product import Product
from .currency import Currency
from .category import Category
from .store import Store
from .bundle import Bundle
from .coupon import Coupon
from .es_product import EsProduct


class EntityQueryset(models.QuerySet):
    def get_available(self):
        return self.filter(active_registry__stock__ne=0)

    def get_unavailable(self):
        return self.filter(Q(active_registry__isnull=True) |
                           Q(active_registry__stock=0))

    def get_active(self):
        return self.filter(active_registry__isnull=False)

    def get_inactive(self):
        return self.filter(active_registry__isnull=True)

    def filter_by_user_perms(self, user, permission):
        synth_permissions = {
            'view_entity': {
                'store': 'view_store',
                'category': 'view_category',
            },
            'view_entity_stocks': {
                'store': 'view_store_stocks',
                'category': 'view_category',
            },
            'is_entity_staff': {
                'store': 'view_store',
                'category': 'is_category_staff',
            }
        }

        assert permission in synth_permissions

        permissions = synth_permissions[permission]

        stores_with_permissions = Store.objects.filter_by_user_perms(
            user, permissions['store'])
        categories_with_permissions = Category.objects.filter_by_user_perms(
            user, permissions['category'])

        return self.filter(
            store__in=stores_with_permissions,
            category__in=categories_with_permissions,
        )

    def get_pending(self):
        return self.get_available().filter(product__isnull=True,
                                           is_visible=True)

    def update(self, *args, **kwargs):
        raise Exception('Queryset level update is disabled on Entity as it '
                        'does not emit pre_save / post_save signals')

    def estimated_sales(self, start_date=None, end_date=None,
                        sorting='normal_price_sum'):
        from solotodo.models import EntityHistory

        ehs = EntityHistory.objects.filter(entity__in=self, stock__gt=0)
        if start_date:
            ehs = ehs.filter(timestamp__gte=start_date)
        if end_date:
            ehs = ehs.filter(timestamp__lte=end_date)

        ehs = ehs.order_by('entity', 'timestamp').select_related('entity')

        movements_by_entity = {}
        for e in self:
            movements_by_entity[e] = {
                'count': 0,
                'normal_price_sum': Decimal(0),
                'offer_price_sum': Decimal(0)
            }

        last_eh_seen = None

        for eh in ehs:
            if not last_eh_seen or last_eh_seen.entity != eh.entity:
                pass
            else:
                units_sold = last_eh_seen.stock - eh.stock
                if units_sold > 0 and units_sold / last_eh_seen.stock < 0.1:
                    movements_by_entity[eh.entity]['count'] += units_sold
                    movements_by_entity[eh.entity]['normal_price_sum'] += \
                        units_sold * last_eh_seen.normal_price
                    movements_by_entity[eh.entity][
                        'offer_price_sum'] += \
                        units_sold * last_eh_seen.offer_price
            last_eh_seen = eh

        result_list = [
            {
                'entity': entity,
                'count': value['count'],
                'normal_price_sum': value['normal_price_sum'],
                'offer_price_sum': value['offer_price_sum']
            }
            for entity, value in movements_by_entity.items()]

        sorted_results = sorted(
            result_list, key=lambda x: x[sorting], reverse=True)

        return sorted_results

    def conflicts(self):
        raw_conflicts = self.filter(product__isnull=False) \
            .get_available() \
            .values('store', 'product', 'cell_plan', 'bundle') \
            .annotate(conflict_count=Count('pk')) \
            .order_by('store', 'product', 'cell_plan', 'bundle') \
            .filter(conflict_count__gt=1)

        store_ids = set()
        product_ids = set()
        bundle_ids = set()

        entities_query = Q()
        for entry in raw_conflicts:
            store_ids.add(entry['store'])
            product_ids.add(entry['product'])
            if entry['cell_plan']:
                product_ids.add(entry['cell_plan'])
            if entry['bundle']:
                bundle_ids.add(entry['bundle'])

            entities_query |= Q(store=entry['store']) & \
                Q(product=entry['product']) & \
                Q(cell_plan=entry['cell_plan']) & \
                Q(bundle=entry['bundle'])

        entities = Entity.objects.get_available().filter(
            entities_query).select_related()

        entities_dict = {}
        for entity in entities:
            key = (entity.store_id, entity.product_id, entity.cell_plan_id,
                   entity.bundle_id)
            if key not in entities_dict:
                entities_dict[key] = []
            entities_dict[key].append(entity)

        stores_dict = iterable_to_dict(Store.objects.filter(pk__in=store_ids))
        products_dict = iterable_to_dict(
            Product.objects.filter(pk__in=product_ids).select_related(
                'instance_model__model__category')
        )
        products_dict[None] = None

        bundles_dict = iterable_to_dict(Bundle.objects.filter(
            pk__in=bundle_ids))
        bundles_dict[None] = None

        result = []
        for entry in raw_conflicts:
            result.append({
                'store': stores_dict[entry['store']],
                'product': products_dict[entry['product']],
                'cell_plan': products_dict[entry['cell_plan']],
                'bundle': bundles_dict[entry['bundle']],
                'entities': entities_dict[(entry['store'], entry['product'],
                                           entry['cell_plan'],
                                           entry['bundle'])]
            })

        return result


class Entity(models.Model):
    CONDITION_CHOICES = [
        ('https://schema.org/DamagedCondition', 'Damaged'),
        ('https://schema.org/NewCondition', 'New'),
        ('https://schema.org/RefurbishedCondition', 'Refurbished'),
        ('https://schema.org/UsedCondition', 'Used'),
        # This is not part of the schema standard
        ('https://schema.org/OpenBoxCondition', 'Open Box'),
    ]
    CONDITION_CHOICES_DICT = dict(CONDITION_CHOICES)

    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    scraped_category = models.ForeignKey(Category, on_delete=models.CASCADE,
                                         related_name='+')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    condition = models.URLField(choices=CONDITION_CHOICES, db_index=True)
    scraped_condition = models.URLField(choices=CONDITION_CHOICES, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE, null=True)
    cell_plan = models.ForeignKey(Product, on_delete=models.CASCADE, null=True,
                                  related_name='+')
    best_coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    related_name='entities_with_coupon')
    active_registry = models.OneToOneField('EntityHistory',
                                           on_delete=models.CASCADE,
                                           related_name='+',
                                           null=True)
    name = models.CharField(max_length=256, db_index=True)
    cell_plan_name = models.CharField(max_length=60, null=True,
                                      blank=True, db_index=True)
    part_number = models.CharField(max_length=50, null=True, blank=True,
                                   db_index=True)
    sku = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    ean = models.CharField(max_length=50, null=True, blank=True)
    key = models.CharField(max_length=256, db_index=True)
    url = models.URLField(max_length=512, db_index=True)
    discovery_url = models.URLField(max_length=512, db_index=True)
    picture_urls = models.TextField(blank=True, null=True)
    description = models.TextField(null=True)
    video_urls = models.TextField(blank=True, null=True)
    flixmedia_id = models.CharField(max_length=256, blank=True, null=True)
    review_count = models.IntegerField(blank=True, null=True)
    review_avg_score = models.FloatField(blank=True, null=True)
    has_virtual_assistant = models.BooleanField(null=True, blank=True)
    sec_qr_codes = models.CharField(
        validators=[validate_comma_separated_integer_list],
        null=True, blank=True, max_length=255,
        db_index=True
    )
    seller = models.CharField(max_length=256, blank=True, null=True,
                              db_index=True)
    is_visible = models.BooleanField(default=True)

    # Metadata

    creation_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    # The last time the entity was associated. Important to leave standalone as
    # it is used for staff payments
    last_association = models.DateTimeField(null=True, blank=True)
    last_association_user = models.ForeignKey(get_user_model(),
                                              on_delete=models.CASCADE,
                                              null=True)

    # Last time a staff accessed the entity in the backend. Used to display a
    # warning to other staff if they try to access it at the same time.
    last_staff_access = models.DateTimeField(null=True, blank=True)
    last_staff_access_user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, null=True,
        related_name='+')

    # The last time the pricing of this entity was updated. Needed because
    # active_registry may be null. It does not match the active_registry date
    # either way because the registry uses the timestamp of the scraping, and
    # this field uses the timestamp of the moment it is updated in the database
    last_pricing_update = models.DateTimeField()

    objects = EntityQueryset.as_manager()

    def __str__(self):
        result = '{} - {}'.format(self.store, self.name)
        if self.cell_plan_name:
            result += ' / {}'.format(self.cell_plan_name)
        result += ' ({})'.format(self.category)

        return result

    @property
    def condition_as_text(self):
        return self.CONDITION_CHOICES_DICT[self.condition]

    def is_available(self):
        if self.active_registry:
            return self.active_registry.stock != 0

        return False

    def update_with_scraped_product(self, scraped_product, sections_dict={},
                                    category=None, currency=None):
        from solotodo.models import EntityHistory, StoreSection, \
            EntitySectionPosition

        assert scraped_product is None or self.key == scraped_product.key

        # If the entity is currently inactive and no scraping information
        # was obtained for it then just return
        if not self.active_registry_id and not scraped_product:
            return

        updated_data = {
            'last_pricing_update': timezone.now(),
        }

        if scraped_product:
            if category is None:
                category = Category.objects.get(
                    storescraper_name=scraped_product.category)

            if currency is None:
                currency = Currency.objects.get(
                    iso_code=scraped_product.currency)

            new_active_registry = EntityHistory.objects.create(
                entity=self,
                stock=scraped_product.stock,
                normal_price=scraped_product.normal_price,
                offer_price=scraped_product.offer_price,
                cell_monthly_payment=scraped_product.cell_monthly_payment,
                timestamp=scraped_product.timestamp,
                picture_count=scraped_product.picture_urls_count(),
                video_count=scraped_product.video_urls_count(),
                review_count=scraped_product.review_count,
                review_avg_score=scraped_product.review_avg_score
            )

            for section_name, position_value in scraped_product.positions:
                store_section = sections_dict.get(section_name)

                if not store_section:
                    store_section = StoreSection.objects.get_or_create(
                        store=self.store,
                        name=section_name
                    )[0]

                EntitySectionPosition.objects.create(
                    section=store_section,
                    entity_history=new_active_registry,
                    value=position_value
                )

            updated_data.update({
                'name': scraped_product.name,
                'scraped_category': category,
                'currency': currency,
                'cell_plan_name': scraped_product.cell_plan_name,
                'part_number': scraped_product.part_number,
                'sku': scraped_product.sku,
                'ean': scraped_product.ean,
                'url': scraped_product.url,
                'discovery_url': scraped_product.discovery_url,
                'picture_urls': scraped_product.picture_urls_as_json(),
                'video_urls': scraped_product.video_urls_as_json(),
                'description': scraped_product.description,
                'scraped_condition': scraped_product.condition,
                'flixmedia_id': scraped_product.flixmedia_id,
                'seller': scraped_product.seller,
                'review_count': scraped_product.review_count,
                'review_avg_score': scraped_product.review_avg_score,
                'has_virtual_assistant': scraped_product.has_virtual_assistant,
                'active_registry': new_active_registry,
            })

            # If the entity condition hasn't been changed manually by the
            # staff, update it with the scraped condition
            if self.condition == self.scraped_condition:
                updated_data['condition'] = scraped_product.condition
        else:
            updated_data.update({
                'active_registry': None
            })

        self.update_keeping_log(updated_data)

    @classmethod
    def create_from_scraped_product(cls, scraped_product, store, category,
                                    currency, sections_dict):
        from solotodo.models import EntityHistory, StoreSection, \
            EntitySectionPosition

        new_entity = cls.objects.create(
            store=store,
            category=category,
            scraped_category=category,
            currency=currency,
            condition=scraped_product.condition,
            scraped_condition=scraped_product.condition,
            name=scraped_product.name,
            cell_plan_name=scraped_product.cell_plan_name,
            part_number=scraped_product.part_number,
            sku=scraped_product.sku,
            ean=scraped_product.ean,
            key=scraped_product.key,
            url=scraped_product.url,
            discovery_url=scraped_product.discovery_url,
            picture_urls=scraped_product.picture_urls_as_json(),
            video_urls=scraped_product.video_urls_as_json(),
            description=scraped_product.description,
            flixmedia_id=scraped_product.flixmedia_id,
            seller=scraped_product.seller,
            review_count=scraped_product.review_count,
            review_avg_score=scraped_product.review_avg_score,
            has_virtual_assistant=scraped_product.has_virtual_assistant,
            is_visible=True,
            last_pricing_update=timezone.now(),
        )

        new_entity_history = EntityHistory.objects.create(
            entity=new_entity,
            stock=scraped_product.stock,
            normal_price=scraped_product.normal_price,
            offer_price=scraped_product.offer_price,
            cell_monthly_payment=scraped_product.cell_monthly_payment,
            timestamp=scraped_product.timestamp,
            picture_count=scraped_product.picture_urls_count(),
            video_count=scraped_product.video_urls_count(),
            review_count=scraped_product.review_count,
            review_avg_score=scraped_product.review_avg_score
        )

        new_entity.active_registry = new_entity_history
        new_entity.save()

        for section_name, position_value in scraped_product.positions:
            store_section = sections_dict.get(section_name)

            if not store_section:
                store_section = StoreSection.objects.get_or_create(
                    store=store,
                    name=section_name
                )[0]

            EntitySectionPosition.objects.create(
                section=store_section,
                entity_history=new_entity_history,
                value=position_value
            )

    def update_keeping_log(self, updated_data, user=None):
        from solotodo.models import EntityLog

        if not user:
            user = get_user_model().get_bot()

        entity_log = EntityLog(
            entity=self,
            user=user,
        )

        save_log = False

        for field, new_value in updated_data.items():
            old_value = getattr(self, field)
            if field in EntityLog.DATA_FIELDS:
                setattr(entity_log, field, old_value)
                if old_value != new_value:
                    save_log = True

            setattr(self, field, new_value)

        self.save()

        if save_log:
            # Fill the remaining fields
            for field in EntityLog.DATA_FIELDS:
                if field not in updated_data:
                    entity_value = getattr(self, field)
                    setattr(entity_log, field, entity_value)
            entity_log.save()

    def save(self, *args, **kwargs):
        is_associated = bool(self.product_id or self.cell_plan_id or
                             self.bundle)

        if bool(self.last_association_user_id) != bool(self.last_association):
            raise IntegrityError('Entity must have both last_association '
                                 'fields or none of them')

        if not self.is_visible and is_associated:
            raise IntegrityError('Entity cannot be associated and be hidden '
                                 'at the same time')

        if not self.product_id and self.cell_plan_id:
            raise IntegrityError('Entity cannot have a cell plan but '
                                 'not a primary product')

        if not self.product_id and self.bundle_id:
            raise IntegrityError('Entity cannot have a bundle plan but '
                                 'not a primary product')

        if is_associated != bool(self.last_association_user_id):
            raise IntegrityError(
                'Associated entities must have association metadata, '
                'non-associated entities must not')

        super(Entity, self).save(*args, **kwargs)

    def update_pricing(self):
        scraper = self.store.scraper

        if self.store.storescraper_extra_args:
            extra_args = json.loads(self.store.storescraper_extra_args)
        else:
            extra_args = None

        scraped_products = scraper.products_for_url(
            self.discovery_url,
            category=self.scraped_category.storescraper_name,
            extra_args=extra_args
        )

        entity_scraped_product = None
        for scraped_product in scraped_products:
            if scraped_product.key == self.key:
                entity_scraped_product = scraped_product
                break

        self.update_with_scraped_product(entity_scraped_product)

    def events(self):
        entity = self
        events = []

        def apply_log_to_entity(log):
            from solotodo.models import EntityLog

            local_changes = []

            for field in EntityLog.DATA_FIELDS:
                entity_value = getattr(entity, field)
                log_value = getattr(log, field)
                if entity_value != log_value:
                    setattr(entity, field, log_value)
                    local_changes.append({
                        'field': field,
                        'old_value': log_value,
                        'new_value': entity_value,
                    })

            return local_changes

        for log in self.entitylog_set.select_related():
            changes = apply_log_to_entity(log)
            events.append({
                'user': log.user,
                'timestamp': log.creation_date,
                'changes': changes
            })

        return events

    def user_has_staff_perms(self, user):
        return user.has_perm('is_category_staff',
                             self.category)

    def user_can_view_stocks(self, user):
        return user.has_perm('view_category', self.category) \
               and user.has_perm('view_store_stocks', self.store)

    def associate(self, user, product, cell_plan=None, bundle=None):
        if not self.is_visible:
            raise IntegrityError('Non-visible cannot be associated')

        if self.product == product and self.cell_plan == cell_plan and \
                self.bundle == bundle:
            raise IntegrityError(
                'Re-associations must be made to a different product / '
                'cell plan / bundle combination')

        if self.category != product.category:
            raise IntegrityError(
                'Entities must be associated to products of the same category')

        if self.cell_plan_name and not cell_plan:
            raise IntegrityError(
                'Entities with cell plan name must specify a plan.')

        now = timezone.now()

        update_dict = {
            'last_association': now,
            'last_association_user': user,
            'product': product,
            'cell_plan': cell_plan,
            'bundle': bundle
        }

        self.update_keeping_log(update_dict, user)

    def dissociate(self, user, reason=None):
        if not self.product:
            raise IntegrityError('Cannot dissociate non-associated entity')
        if reason and self.last_association_user == user:
            raise IntegrityError(
                'Reason must not be present if the last association user is '
                'the same as the one dissociating the entity')

        update_dict = {
            'last_association': None,
            'last_association_user': None,
            'product': None,
            'cell_plan': None,
            'bundle': None
        }

        if reason:
            self.last_association_user.send_entity_dissociation_mail(
                self, user, reason)

        self.update_keeping_log(update_dict, user)

    def associate_related_cell_entities(self, user):
        from django.conf import settings

        assert self.cell_plan_name
        assert self.product

        print('Associating related entities for: {}'.format(self))

        other_entities = Entity.objects.filter(
            store=self.store,
            name=self.name
        ).exclude(
            pk=self.pk
        )

        other_cell_plan_names = [e.cell_plan_name for e in other_entities]

        cell_plan_category = Category.objects.get(
            pk=settings.CELL_PLAN_CATEGORY)

        matching_cell_plans = EsProduct.category_search(cell_plan_category)\
            .filter(
            'terms',
            specs__association_name=other_cell_plan_names)[:100] \
            .execute()

        cell_plan_ids = [cell_plan.product_id
                         for cell_plan in matching_cell_plans]
        cell_plans = Product.objects.filter(pk__in=cell_plan_ids)
        cell_plans_dict = iterable_to_dict(cell_plans)

        cell_plans_dict = {
            cell_plan.specs['association_name']:
                cell_plans_dict[cell_plan.product_id]
            for cell_plan in matching_cell_plans
        }

        print('Related entities found:')
        for entity in other_entities:
            print('* {}'.format(entity))

            if entity.cell_plan_name in cell_plans_dict:
                cell_plan = cell_plans_dict[entity.cell_plan_name]
                print('Matching plan found: {}'.format(cell_plan))
                if entity.product != self.product or \
                        entity.cell_plan != cell_plan or \
                        entity.bundle != self.bundle:
                    entity.associate(user, self.product, cell_plan,
                                     self.bundle)
            else:
                print('No matching cell plan found')

    def picture_urls_as_list(self):
        if not self.picture_urls:
            return None
        return json.loads(self.picture_urls)

    def video_urls_as_list(self):
        if not self.video_urls:
            return None
        return json.loads(self.video_urls)

    def affiliate_url(self, soicos_prefix=""):
        from django.conf import settings

        linio_settings = settings.LINIO_AFFILIATE_SETTINGS
        affiliate_ids = settings.AFFILIATE_IDS

        if self.store_id == linio_settings['STORE_ID']:
            if '?' in self.url:
                separator = '&'
            else:
                separator = '?'

            target_url = '{}{}utm_source=affiliates&utm_medium=hasoffers&' \
                         'utm_campaign={}&aff_sub=' \
                         ''.format(self.url, separator,
                                   linio_settings['AFFILIATE_ID'])

            url = 'https://linio.go2cloud.org/aff_c?offer_id=18&aff_id={}' \
                  '&url={}'.format(linio_settings['AFFILIATE_ID'],
                                   urllib.parse.quote(target_url))
            return url
        elif self.store_id in affiliate_ids:
            target_url = self.url
            affiliate_id = affiliate_ids[self.store_id]
            url = 'https://ad.soicos.com/{}?dl={}&trackerID={}{}'.format(
                affiliate_id, urllib.parse.quote(target_url), soicos_prefix,
                self.active_registry_id)

            return url

        return None

    def update_sec_qr_codes(self):
        if self.store.storescraper_extra_args:
            extra_args = json.loads(self.store.storescraper_extra_args)
        else:
            extra_args = None
        session = session_with_proxy(extra_args)
        if not extra_args or 'user-agent' not in extra_args:
            session.headers['user-agent'] = \
                ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                 'AppleWebKit/537.36 (KHTML, like Gecko) '
                 'Chrome/116.0.0.0 Safari/537.36')

        picture_urls = self.picture_urls_as_list() or []

        qr_codes = set()
        for picture_url in picture_urls:
            response = session.get(picture_url, timeout=10)
            if response.status_code != 200:
                continue
            image = Image.open(io.BytesIO(response.content))
            decoded_qr_codes = decode(image)
            for decoded_qr_code in decoded_qr_codes:
                if decoded_qr_code.type != 'QRCODE':
                    continue
                qr_url = decoded_qr_code.data.decode('UTF-8')
                qr_code_match = re.match(
                    r'https://ww6.sec.cl/qr/qr.do\?a=prod&i=(\d+)$', qr_url)
                if not qr_code_match:
                    continue
                qr_code = str(int(qr_code_match.groups()[0]))
                qr_codes.add(qr_code)

        if qr_codes:
            sec_qr_codes = ','.join(qr_codes)
        else:
            sec_qr_codes = '0'

        self.sec_qr_codes = sec_qr_codes
        self.save()

    def sec_info(self):
        if not self.sec_qr_codes or self.sec_qr_codes == '0':
            return []
        sec_qr_codes = self.sec_qr_codes.split(',')
        sec_entries = []
        for sec_qr_code in sec_qr_codes:
            zeros = 13 - len(sec_qr_code)
            sec_url = 'https://ww6.sec.cl/qr/qr.do?a=prod&i={}{}'.format(
                zeros * '0', sec_qr_code
            )
            raw_sec_data = fetch_sec_fields(sec_qr_code)
            sec_entry = {
                'code': sec_qr_code,
                'sec_url': sec_url,
                'brands': raw_sec_data['Marcas'],
                'models': raw_sec_data['Modelos'],
            }
            sec_entries.append(sec_entry)
        return sec_entries

    class Meta:
        app_label = 'solotodo'
        ordering = ('creation_date', )
        unique_together = ('store', 'key')
        permissions = [
            ('backend_list_entities', 'Can view entity list in backend'),
            ('backend_view_entity_conflicts',
             'Can view entity conflicts in backend'),
            ('backend_view_entity_estimated_sales',
             'Can view the entity estimated sales interface in backend'
             ),
            ('backend_view_pending_entities',
             'Can view the pending entities interface in the backend'
             ),
        ]
