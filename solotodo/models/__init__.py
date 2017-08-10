from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from .language import Language
from .solotodo_user import SoloTodoUser
from .currency import Currency
from .country import Country
from .store_type import StoreType
from .product_type_tier import ProductTypeTier
from .store import Store
from .product_type import ProductType
from .product import Product
from .entity import Entity
from .entity_history import EntityHistory
from .store_update_log import StoreUpdateLog


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
