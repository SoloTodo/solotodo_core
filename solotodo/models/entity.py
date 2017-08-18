from django.contrib.auth import get_user_model
from django.db import models, IntegrityError
from django.db.models import Q
from django.utils import timezone

from solotodo.models.product import Product
from solotodo.models.currency import Currency
from solotodo.models.product_type import ProductType
from solotodo.models.store import Store


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
    product_type = models.ForeignKey(ProductType)
    scraped_product_type = models.ForeignKey(ProductType, related_name='+')
    currency = models.ForeignKey(Currency)
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
    picture_url = models.URLField(max_length=512, blank=True, null=True)
    description = models.TextField()
    is_visible = models.BooleanField(default=True)
    latest_association_user = models.ForeignKey(get_user_model(), null=True)
    latest_association_date = models.DateTimeField(null=True, blank=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    objects = EntityQueryset.as_manager()

    def __str__(self):
        result = '{} - {}'.format(self.store, self.name)
        if self.cell_plan_name:
            result += ' / {}'.format(self.cell_plan_name)
        result += ' ({})'.format(self.product_type)

        return result

    def is_available(self):
        if self.active_registry:
            return self.active_registry.stock != 0

        return False

    def update_with_scraped_product(self, scraped_product,
                                    product_type, currency):
        from solotodo.models import EntityHistory

        assert scraped_product is None or self.key == scraped_product.key

        if self.active_registry and \
                self.active_registry.date == timezone.now().date():
            current_active_registry = self.active_registry
        else:
            current_active_registry = None

        if scraped_product:
            self.scraped_product_type = product_type
            self.currency = currency
            self.name = scraped_product.name
            self.cell_plan_name = scraped_product.cell_plan_name
            self.part_number = scraped_product.part_number
            self.sku = scraped_product.sku
            self.url = scraped_product.url
            self.discovery_url = scraped_product.discovery_url
            self.picture_url = scraped_product.picture_url
            self.description = scraped_product.description

            if not current_active_registry:
                current_active_registry = EntityHistory(
                    entity=self,
                    date=timezone.now().date()
                )

            current_active_registry.stock = scraped_product.stock
            current_active_registry.normal_price = scraped_product.normal_price
            current_active_registry.offer_price = scraped_product.offer_price
            current_active_registry.cell_monthly_payment = \
                scraped_product.cell_monthly_payment
            current_active_registry.save()

            # This is redundant if the current_active_registry is the same
            # as self.active_registry, but doesn't impact performance
            self.active_registry = current_active_registry

            self.save()
        else:
            self.active_registry = None
            self.save()
            if current_active_registry:
                current_active_registry.delete()

    @classmethod
    def create_from_scraped_product(cls, scraped_product, store, product_type,
                                    currency):
        from solotodo.models import EntityHistory

        new_entity = cls.objects.create(
            store=store,
            product_type=product_type,
            scraped_product_type=product_type,
            currency=currency,
            name=scraped_product.name,
            cell_plan_name=scraped_product.cell_plan_name,
            part_number=scraped_product.part_number,
            sku=scraped_product.sku,
            key=scraped_product.key,
            url=scraped_product.url,
            discovery_url=scraped_product.discovery_url,
            picture_url=scraped_product.picture_url,
            description=scraped_product.description,
            is_visible=True,
        )

        new_entity_history = EntityHistory.objects.create(
            entity=new_entity,
            date=timezone.now().date(),
            stock=scraped_product.stock,
            normal_price=scraped_product.normal_price,
            offer_price=scraped_product.offer_price,
            cell_monthly_payment=scraped_product.cell_monthly_payment
        )

        new_entity.active_registry = new_entity_history
        new_entity.save()

    def save(self, *args, **kwargs):
        is_associated = self.product or self.cell_plan

        if self.latest_association_user and not self.latest_association_date:
            raise IntegrityError('Resolved entity must have a date')

        if not self.latest_association_user and self.latest_association_date:
            raise IntegrityError('Resolved entity must have a resolver')

        if not self.is_visible and is_associated:
            raise IntegrityError('Entity cannot be associated and be hidden '
                                 'at the same time')

        if not self.product and self.cell_plan:
            raise IntegrityError('Entity cannot have a secondary product but '
                                 'not a primary association')

        if is_associated and not self.latest_association_user:
            raise IntegrityError('Entity cannot be associated to product '
                                 'without resolver')

        if not is_associated and self.latest_association_user:
            raise IntegrityError('Entity cannot have a resolver without '
                                 'being associated')

        super(Entity, self).save(*args, **kwargs)

    class Meta:
        app_label = 'solotodo'
        unique_together = ('store', 'key')
        permissions = [
            ('backend_list_entity', 'Can view entity list in backend'),
        ]
