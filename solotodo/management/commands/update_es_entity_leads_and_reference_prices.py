from datetime import timedelta

from django.core.management import BaseCommand
from django.db.models import Count, Min
from django.utils import timezone

from solotodo.models import Lead, EsEntity, Currency, EntityHistory


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--leads_days", nargs="?", type=int)
        parser.add_argument("--reference_price_start_hours", nargs="?", type=int)
        parser.add_argument("--reference_price_end_hours", nargs="?", type=int)

    def handle(self, *args, **options):
        days = options["leads_days"] or 3
        start_hours = options["reference_price_start_hours"] or 84
        end_hours = options["reference_price_end_hours"] or 36

        leads = (
            Lead.objects.filter(timestamp__gte=timezone.now() - timedelta(days=days))
            .order_by("entity_history__entity")
            .values("entity_history__entity")
            .annotate(c=Count("*"))
        )
        leads_dict = {x["entity_history__entity"]: x["c"] for x in leads}

        currencies_exchange_rates = {
            x.id: float(x.exchange_rate) for x in Currency.objects.all()
        }

        reference_prices = (
            EntityHistory.objects.filter(
                timestamp__gte=timezone.now() - timedelta(hours=start_hours),
                timestamp__lte=timezone.now() - timedelta(hours=end_hours),
            )
            .order_by("entity")
            .values("entity")
            .annotate(
                min_normal_price=Min("normal_price"), min_offer_price=Min("offer_price")
            )
        )

        reference_prices_dict = {
            x["entity"]: (x["min_normal_price"], x["min_offer_price"])
            for x in reference_prices
        }

        es_results = EsEntity.search()
        result_count = es_results.count()

        for idx, es_hit in enumerate(es_results.scan()):
            print("{} / {}".format(idx + 1, result_count))
            leads = leads_dict.get(es_hit.entity_id, 0)

            reference_normal_price, reference_offer_price = reference_prices_dict.get(
                es_hit.entity_id, (es_hit.normal_price, es_hit.offer_price)
            )
            exchange_rate = currencies_exchange_rates[es_hit.currency_id]

            es_entity = EsEntity(**es_hit.to_dict(), meta=es_hit.meta.to_dict())
            es_entity.leads = leads
            es_entity.reference_normal_price = float(reference_normal_price)
            es_entity.reference_offer_price = float(reference_offer_price)
            es_entity.reference_normal_price_usd = (
                es_entity.reference_normal_price / exchange_rate
            )
            es_entity.reference_offer_price_usd = (
                es_entity.reference_offer_price / exchange_rate
            )
            # print(es_entity.leads)
            # print(es_entity.reference_normal_price)
            # print(es_entity.reference_offer_price)
            # print(es_entity.reference_normal_price_usd)
            # print(es_entity.reference_offer_price_usd)

            es_entity.save()
