from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from rest_framework.authtoken.models import Token

from metamodel.models import MetaModel, InstanceModel
from metamodel.signals import instance_model_saved

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
from .product import Product
from .rating import Rating
from .materialized_entity import MaterializedEntity
from .entity import Entity
from .entity_history import EntityHistory
from .entity_log import EntityLog
from .store_update_log import StoreUpdateLog
from .lead import Lead
from .category_specs_filter import CategorySpecsFilter
from .category_specs_order import CategorySpecsOrder
from .visit import Visit


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def handle_user_creation(sender, instance=None, created=False, **kwargs):
    if created:
        # Create Authorization token
        Token.objects.create(user=instance)
        # Add user to base group with basic permissions
        group, created = Group.objects.get_or_create(name='base')
        instance.groups.add(group)


@receiver(instance_model_saved)
def create_or_update_product(instance_model, created, creator_id, **kwargs):
    category_models = [c.meta_model for c in Category.objects.all()]

    if instance_model.model in category_models:
        try:
            existing_product = Product.objects.get(
                instance_model=instance_model)
            existing_product.save()
        except Product.DoesNotExist:
            new_product = Product()
            new_product.instance_model = instance_model
            new_product.save(creator_id=creator_id)


@receiver(pre_delete, sender=InstanceModel)
def delete_product_from_es(sender, instance, using, **kwargs):
    category_models = MetaModel.objects.filter(category__isnull=False)

    if instance.model in category_models:
        associated_product = Product.objects.get(instance_model=instance)
        associated_product.delete_from_elasticsearch()


@receiver(m2m_changed, sender=SoloTodoUser.preferred_stores.through)
def update_preferred_stores_last_updated(sender, instance, *args, **kwargs):
    instance.preferred_stores_last_updated = timezone.now()
    instance.save()
