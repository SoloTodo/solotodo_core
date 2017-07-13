from django.contrib.auth import get_user_model
from django.db import models, IntegrityError
from django.utils import timezone

from solotodo.models.product import Product
from solotodo.models.currency import Currency
from solotodo.models.product_type import ProductType
from solotodo.models.store import Store


class Entity(models.Model):
    store = models.ForeignKey(Store)
    product_type = models.ForeignKey(ProductType)
    scraped_product_type = models.ForeignKey(ProductType, related_name='+')
    currency = models.ForeignKey(Currency)
    product = models.ForeignKey(Product, null=True)
    cell_plan = models.ForeignKey(Product, null=True, related_name='+')
    # latest_registry is nullable ONLY to prevent a chicken-egg problem with
    # EntityHistory, which has a ForeignKey that points to Entity. One
    # of these FK must be nullable to allow new entities to be saved with their
    # corresponding initial histories.
    # Overriden save method prevents persisting this field as None by default
    latest_registry = models.OneToOneField('EntityHistory', related_name='+',
                                           null=True)

    name = models.CharField(max_length=256, db_index=True)
    cell_plan_name = models.CharField(max_length=50, null=True,
                                      blank=True, db_index=True)
    part_number = models.CharField(max_length=50, null=True, blank=True,
                                   db_index=True)
    sku = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    key = models.CharField(max_length=256, db_index=True)
    url = models.URLField(max_length=512, unique=True, db_index=True)
    discovery_url = models.URLField(max_length=512, unique=True, db_index=True)
    description = models.TextField()
    is_visible = models.BooleanField(default=True)
    latest_association_user = models.ForeignKey(get_user_model(), null=True)
    latest_association_date = models.DateTimeField(null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        result = '{} - {}'.format(self.store, self.name)
        if self.cell_plan_name:
            result += ' / {}'.format(self.cell_plan_name)
        result += ' ({})'.format(self.product_type)

        return result

    def update_with_scraped_product(self, scraped_product,
                                    product_type, currency):
        from solotodo.models import EntityHistory

        assert scraped_product is None or self.key == scraped_product.key

        should_save_self = False

        if self.latest_registry.date == timezone.now().date():
            latest_registry = self.latest_registry
        else:
            latest_registry = EntityHistory(
                entity=self,
                date=timezone.now().date()
            )
            self.latest_registry = latest_registry
            should_save_self = True

        if scraped_product:
            self.scraped_product_type = product_type
            self.currency = currency
            self.name = scraped_product.name
            self.cell_plan_name = scraped_product.cell_plan_name
            self.part_number = scraped_product.part_number
            self.sku = scraped_product.sku
            self.url = scraped_product.url
            self.discovery_url = scraped_product.discovery_url
            self.description = scraped_product.description

            should_save_self = True

            latest_registry.stock = scraped_product.stock
            latest_registry.normal_price = scraped_product.normal_price
            latest_registry.offer_price = scraped_product.offer_price
            latest_registry.cell_monthly_payment = \
                scraped_product.cell_monthly_payment
        else:
            latest_registry.stock = 0
            latest_registry.normal_price = None
            latest_registry.offer_price = None
            latest_registry.cell_monthly_payment = None

        latest_registry.save()
        if should_save_self:
            self.save()

    @classmethod
    def create_from_scraped_product(cls, scraped_product, store, product_type, currency):
        from solotodo.models import EntityHistory

        new_entity = cls(
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
            description=scraped_product.description,
            is_visible=True,
        )

        new_entity.save(allow_null_latest_registry=True)

        new_entity_history = EntityHistory.objects.create(
            entity=new_entity,
            date=timezone.now().date(),
            stock=scraped_product.stock,
            normal_price=scraped_product.normal_price,
            offer_price=scraped_product.offer_price,
            cell_monthly_payment=scraped_product.cell_monthly_payment
        )

        new_entity.latest_registry = new_entity_history
        new_entity.save()

    def save(self, allow_null_latest_registry=False, *args, **kwargs):
        is_associated = self.product or self.cell_plan

        if not self.latest_registry and not allow_null_latest_registry:
            raise IntegrityError('entity.latest_registry may not be NULL '
                                 'unless explicitly stated in the save call')

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
