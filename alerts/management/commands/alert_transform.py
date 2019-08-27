from django.core.management import BaseCommand

from alerts.models import ProductPriceAlert, AnonymousAlert, UserAlert


class Command(BaseCommand):
    def handle(self, *args, **options):
        a_alerts = AnonymousAlert.objects.order_by('id')

        for alert in a_alerts:
            print(alert.id)
            product = alert.alert.product
            stores = alert.alert.stores.all()
            email = alert.email
            creation_date = alert.alert.creation_date

            new_alert = ProductPriceAlert.objects.create(
                product=product,
                email=email)

            new_alert.stores.set(stores)
            new_alert.creation_date = creation_date
            new_alert.save()

            new_alert.update_active_history()

        u_alerts = UserAlert.objects.order_by('id')

        for alert in u_alerts:
            print(alert.id)
            if alert.entity:
                product = alert.entity.product
                stores = [alert.entity.store]
            else:
                product = alert.alert.product
                stores = alert.alert.stores.all()

            user = alert.user
            creation_date = alert.alert.creation_date

            new_alert = ProductPriceAlert.objects.create(
                product=product,
                user=user)

            new_alert.stores.set(stores)
            new_alert.creation_date = creation_date
            new_alert.save()

            new_alert.update_active_history()
