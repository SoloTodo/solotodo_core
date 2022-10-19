from django.core.management import BaseCommand

from solotodo.models import Coupon


class Command(BaseCommand):
    def handle(self, *args, **options):
        Coupon.apply_all_coupons()
