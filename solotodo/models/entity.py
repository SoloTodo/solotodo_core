import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, IntegrityError
from django.db.models import Q
from django.utils import timezone

from .product import Product
from .currency import Currency
from .category import Category
from .store import Store
from .entity_state import EntityState


class EntityQueryset(models.QuerySet):
    def get_available(self):
        return self.exclude(Q(active_registry__isnull=True) |
                            Q(active_registry__stock=0))

    def get_unavailable(self):
        return self.filter(Q(active_registry__isnull=True) |
                           Q(active_registry__stock=0))

    def get_active(self):
        return self.filter(active_registry__isnull=False)

    def get_inactive(self):
        return self.filter(active_registry__isnull=True)


class Entity(models.Model):
    store = models.ForeignKey(Store)
    category = models.ForeignKey(Category)
    scraped_category = models.ForeignKey(Category, related_name='+')
    currency = models.ForeignKey(Currency)
    state = models.ForeignKey(EntityState)
    product = models.ForeignKey(Product, null=True)
    cell_plan = models.ForeignKey(Product, null=True, related_name='+')
    active_registry = models.OneToOneField('EntityHistory', related_name='+',
                                           null=True)
    name = models.CharField(max_length=256, db_index=True)
    cell_plan_name = models.CharField(max_length=50, null=True,
                                      blank=True, db_index=True)
    part_number = models.CharField(max_length=50, null=True, blank=True,
                                   db_index=True)
    sku = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    key = models.CharField(max_length=256, db_index=True)
    url = models.URLField(max_length=512, db_index=True)
    discovery_url = models.URLField(max_length=512, db_index=True)
    picture_urls = models.TextField(blank=True, null=True)
    description = models.TextField(null=True)
    is_visible = models.BooleanField(default=True)

    # Metadata

    creation_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    # The last time the entity was associated. Important to leave standalone as
    # it is used for staff payments
    last_association = models.DateTimeField(null=True, blank=True)
    last_association_user = models.ForeignKey(get_user_model(), null=True)

    # Last time a staff accessed the entity in the backend. Used to display a
    # warning to other staff if they try to access it at the same time.
    last_staff_access = models.DateTimeField(null=True, blank=True)
    last_staff_access_user = models.ForeignKey(
        get_user_model(), null=True, related_name='+')

    # Last time a staff made a change to the entity (change category,
    # visibility, association). Used to warn other staff when someone is
    # working on an entity.
    last_staff_change = models.DateTimeField(null=True, blank=True)
    last_staff_change_user = models.ForeignKey(
        get_user_model(), null=True, related_name='+')

    # The last time the pricing of this entity was updated. Needed because
    # active_registry may be null. It does not match the active_registry date
    # either way because the registry uses the timestamp of the scraping, and
    # this field uses the timestamp of the moment it is updated in the database
    last_pricing_update = models.DateTimeField()
    last_pricing_update_user = models.ForeignKey(
        get_user_model(), related_name='+')

    objects = EntityQueryset.as_manager()

    def __str__(self):
        result = '{} - {}'.format(self.store, self.name)
        if self.cell_plan_name:
            result += ' / {}'.format(self.cell_plan_name)
        result += ' ({})'.format(self.category)

        return result

    def is_available(self):
        if self.active_registry:
            return self.active_registry.stock != 0

        return False

    def update_with_scraped_product(self, scraped_product,
                                    category=None, currency=None,
                                    user=None):
        from solotodo.models import EntityHistory

        assert scraped_product is None or self.key == scraped_product.key

        if not user:
            user = get_user_model().get_bot()

        updated_data = {
            'last_pricing_update': timezone.now(),
            'last_pricing_update_user': user
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
            )

            updated_data.update({
                'name': scraped_product.name,
                'scraped_category': category,
                'currency': currency,
                'cell_plan_name': scraped_product.cell_plan_name,
                'part_number': scraped_product.part_number,
                'sku': scraped_product.sku,
                'url': scraped_product.url,
                'discovery_url': scraped_product.discovery_url,
                'picture_urls': scraped_product.picture_urls_as_json(),
                'description': scraped_product.description,
                'active_registry': new_active_registry,
            })
        else:
            updated_data.update({
                'active_registry': None
            })

        self.update_keeping_log(updated_data)

    @classmethod
    def create_from_scraped_product(cls, scraped_product, store, category,
                                    currency, states_dict=None):
        from solotodo.models import EntityHistory

        if states_dict:
            state = states_dict[scraped_product.state]
        else:
            state = EntityState.objects.get(
                storescraper_name=scraped_product.state)

        new_entity = cls.objects.create(
            store=store,
            category=category,
            scraped_category=category,
            currency=currency,
            state=state,
            name=scraped_product.name,
            cell_plan_name=scraped_product.cell_plan_name,
            part_number=scraped_product.part_number,
            sku=scraped_product.sku,
            key=scraped_product.key,
            url=scraped_product.url,
            discovery_url=scraped_product.discovery_url,
            picture_urls=scraped_product.picture_urls_as_json(),
            description=scraped_product.description,
            is_visible=True,
            last_pricing_update=timezone.now(),
            last_pricing_update_user=get_user_model().get_bot()
        )

        new_entity_history = EntityHistory.objects.create(
            entity=new_entity,
            stock=scraped_product.stock,
            normal_price=scraped_product.normal_price,
            offer_price=scraped_product.offer_price,
            cell_monthly_payment=scraped_product.cell_monthly_payment,
            timestamp=scraped_product.timestamp
        )

        new_entity.active_registry = new_entity_history
        new_entity.save()

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
        is_associated = bool(self.product_id or self.cell_plan_id)

        if bool(self.last_association_user_id) != bool(self.last_association):
            raise IntegrityError('Entity must have both last_association '
                                 'fields or none of them')

        if not self.is_visible and is_associated:
            raise IntegrityError('Entity cannot be associated and be hidden '
                                 'at the same time')

        if not self.product_id and self.cell_plan_id:
            raise IntegrityError('Entity cannot have a cell plan but '
                                 'not a primary product')

        if is_associated != bool(self.last_association_user_id):
            raise IntegrityError(
                'Associated entities must have association metadata, '
                'non-associated entities must not')

        super(Entity, self).save(*args, **kwargs)

    def update_pricing(self, user=None):
        if not user:
            user = get_user_model().get_bot()

        scraper = self.store.scraper
        scraped_products = scraper.products_for_url(
            self.discovery_url,
            category=self.scraped_category.storescraper_name,
            extra_args=self.store.storescraper_extra_args
        )

        entity_scraped_product = None
        for scraped_product in scraped_products:
            if scraped_product.key == self.key:
                entity_scraped_product = scraped_product
                break

        self.update_with_scraped_product(entity_scraped_product, user=user)

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
                             self.category) \
               and user.has_perm('is_store_staff', self.store)

    def user_can_view_stocks(self, user):
        return user.has_perm('view_category_stocks', self.category) \
               and user.has_perm('view_store_stocks', self.store)

    def associate(self, user, product, cell_plan=None):
        if not self.is_visible:
            raise IntegrityError('Non-visible cannot be associated')

        if self.product == product and self.cell_plan == cell_plan:
            raise IntegrityError(
                'Re-associations must be made to a different product / '
                'cell plan pair')

        if self.category != product.category:
            raise IntegrityError(
                'Entities must be associated to products of the same category')

        now = timezone.now()

        update_dict = {
            'last_association': now,
            'last_association_user': user,
            'last_staff_change': now,
            'last_staff_change_user': user,
            'product': product,
            'cell_plan': cell_plan
        }

        self.update_keeping_log(update_dict, user)

    def dissociate(self, user, reason=None):
        if not self.product:
            raise IntegrityError('Cannot dissociate non-associated entity')
        if reason and self.last_association_user == user:
            raise IntegrityError(
                'Reason must not be present if the last association user is '
                'the same as the one dissociating the entity')

        now = timezone.now()

        update_dict = {
            'last_association': None,
            'last_association_user': None,
            'last_staff_change': now,
            'last_staff_change_user': user,
            'product': None,
            'cell_plan': None
        }

        if self.last_association_user != user:
            self.last_association_user.send_entity_dissociation_mail(
                self, user, reason)

        self.update_keeping_log(update_dict, user)

    def picture_urls_as_list(self):
        if not self.picture_urls:
            return None
        return json.loads(self.picture_urls)

    class Meta:
        app_label = 'solotodo'
        unique_together = ('store', 'key')
        permissions = [
            ('backend_list_entities', 'Can view entity list in backend'),
        ]
