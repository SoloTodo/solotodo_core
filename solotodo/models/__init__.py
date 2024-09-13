from guardian import core
from solotodo_core.guardian_patched_object_permission_checker import (
    GuardianPatchedObjectPermissionChecker,
)

core.ObjectPermissionChecker = GuardianPatchedObjectPermissionChecker

from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Lookup
from django.db.models.fields import Field
from elasticsearch import NotFoundError

from rest_framework.authtoken.models import Token

from metamodel.models import MetaModel
from metamodel.signals import instance_model_saved

from solotodo.signals import product_saved

from .website import Website
from .number_format import NumberFormat
from .language import Language
from .solotodo_user import SoloTodoUser
from .currency import Currency
from .country import Country
from .store_type import StoreType
from .category_tier import CategoryTier
from .store import Store
from .category import Category
from .bundle import Bundle
from .brand import Brand
from .product import Product
from .product_picture import ProductPicture
from .rating import Rating
from .entity import Entity
from .entity_history import EntityHistory
from .entity_log import EntityLog
from .store_update_log import StoreUpdateLog
from .lead import Lead
from .category_specs_filter import CategorySpecsFilter
from .category_specs_order import CategorySpecsOrder
from .visit import Visit
from .store_section import StoreSection
from .entity_section_position import EntitySectionPosition
from .product_video import ProductVideo
from .coupon import Coupon
from .product_field_watcher import ProductFieldWatcher

# ElasticSearch DSL persistence models
from .es_product_entities import EsProductEntities
from .es_product import EsProduct
from .es_entity import EsEntity


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def handle_user_creation(sender, instance=None, created=False, **kwargs):
    if created:
        # Create Authorization token
        Token.objects.create(user=instance)
        # Add user to base group with basic permissions
        group, created = Group.objects.get_or_create(name=settings.DEFAULT_GROUP_NAME)
        instance.groups.add(group)


@receiver(instance_model_saved)
def create_or_update_product(instance_model, created, creator_id, **kwargs):
    category_models = MetaModel.objects.filter(category__isnull=False)

    if instance_model.model in category_models:
        try:
            existing_product = Product.objects.get(instance_model=instance_model)
            existing_product.save()
        except Product.DoesNotExist:
            new_product = Product()
            new_product.instance_model = instance_model
            new_product.save(creator_id=creator_id)


@receiver(product_saved)
def update_product_in_es(product, es_document, **kwargs):
    EsProduct.from_product(product, es_document).save()


@receiver(post_delete, sender=Product)
def delete_product_from_es(sender, instance, using, **kwargs):
    EsProduct.get_by_product_id(instance.id).delete()


@receiver(m2m_changed, sender=SoloTodoUser.preferred_stores.through)
def update_preferred_stores_last_updated(sender, instance, *args, **kwargs):
    instance.preferred_stores_last_updated = timezone.now()
    instance.save()


@receiver(post_save, sender=Entity)
def update_entity_in_es(sender, instance, **kwargs):
    if EsEntity.should_entity_be_indexed(instance):
        EsEntity.from_entity(instance).save()
    else:
        try:
            EsEntity.get_by_entity_id(instance.id).delete()
        except NotFoundError:
            pass


@receiver(post_delete, sender=Entity)
def delete_entity_from_es(sender, instance, using, **kwargs):
    try:
        EsEntity.get_by_entity_id(instance.id).delete()
    except NotFoundError:
        pass


@Field.register_lookup
class NotEqual(Lookup):
    lookup_name = "ne"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return "%s <> %s" % (lhs, rhs), params
