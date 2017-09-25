from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from metamodel.models import MetaModel
from metamodel.signals import instance_model_saved

from .api_client import ApiClient
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
from .entity_state import EntityState
from .entity import Entity
from .entity_history import EntityHistory
from .entity_log import EntityLog
from .store_update_log import StoreUpdateLog
from .entity_visit import EntityVisit


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def handle_user_creation(sender, instance=None, created=False, **kwargs):
    if created:
        # Create Authorization token
        Token.objects.create(user=instance)
        # Add user to base group with basic permissions
        group = Group.objects.get(name='base')
        instance.groups.add(group)


@receiver(instance_model_saved)
def create_or_update_product(instance_model, created, creator_id, **kwargs):
    print('hooked')
    category_models = [c.meta_model for c in Category.objects.all()]

    if instance_model.model in category_models:
        try:
            existing_product = Product.objects.get(
                instance_model=instance_model)
            existing_product.save()
        except Product.DoesNotExist:
            print('new product')
            new_product = Product()
            new_product.instance_model = instance_model
            new_product.save(creator_id=creator_id)
