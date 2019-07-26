import csv

from django.core.management import BaseCommand
from django.db.models import Count, Avg

from dateutil.rrule import rrule, MONTHLY
from dateutil.relativedelta import relativedelta
from datetime import datetime

from solotodo.models import EntityHistory, Product, Lead, Visit


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--category_id', type=int)
        parser.add_argument('--start', type=str)
        parser.add_argument('--end', type=str)

    def handle(self, *args, **options):
        category_id = options['category_id']
        start = options['start'].split('-')
        end = options['end'].split('-')

        start_date = datetime(int(start[0]), int(start[1]), 1)
        end_date = datetime(int(end[0]), int(end[1]), 1)

        months = list(rrule(MONTHLY, dtstart=start_date, until=end_date))

        category_specs_dict = {
            15: ['r_format_unicode',
                 'energy_efficiency_unicode',
                 'consumption',
                 'refrigerator_capacity',
                 'freezer_capacity'],
            11: [
                'display_unicode',
                'size_value',
                'resolution_unicode',
                'is_smart_tv',
                'energy_efficiency_unicode',
                'average_monthly_consumption'
            ]
        }

        with open('government_report.csv', mode='w') as csv_file:
            for month_start in months:
                month_end = month_start + relativedelta(months=1)
                ehs = EntityHistory.objects.filter(
                    entity__category=category_id,
                    entity__store__country=1,
                    entity__product__isnull=False,
                    entity__store__type=1,
                    timestamp__gte=month_start,
                    timestamp__lt=month_end
                ).get_available()

                aggs = ehs\
                    .order_by('entity__product')\
                    .values('entity__product')\
                    .annotate(
                        price_avg=Avg('normal_price'),
                    )

                product_ids = [a['entity__product'] for a in aggs]
                products = Product.objects.filter(id__in=product_ids)
                Product.prefetch_specs(products)
                products_dict = {p.id: p for p in products}

                leads_aggs = Lead.objects\
                    .filter(
                        entity_history__entity__product__in=products,
                        timestamp__gte=month_start,
                        timestamp__lt=month_end,
                        website=2)\
                    .order_by('entity_history__entity__product')\
                    .values('entity_history__entity__product')\
                    .annotate(count=Count('entity_history__entity__product'))

                leads_dict = {
                    l['entity_history__entity__product']: l['count']
                    for l in leads_aggs
                }

                visits_aggs = Visit.objects \
                    .filter(
                        product__in=products,
                        timestamp__gte=month_start,
                        timestamp__lt=month_end,
                        website=2) \
                    .order_by('product') \
                    .values('product') \
                    .annotate(count=Count('product'))

                visits_dict = {
                    v['product']: v['count']
                    for v in visits_aggs
                }

                category_specs = category_specs_dict[category_id]
                csv_writer = csv.writer(csv_file, delimiter=',')

                for agg in aggs:
                    price_avg = agg['price_avg']
                    product = products_dict[agg['entity__product']]
                    specs = product.specs

                    leads_count = leads_dict.get(product.id, 0)
                    visits_count = visits_dict.get(product.id, 0)

                    row = [product.name]

                    for spec_key in category_specs:
                        row.append(specs[spec_key])

                    if month_start.month < 10:
                        month_str = '0{}'.format(month_start.month)
                    else:
                        month_str = str(month_start.month)

                    row.append(price_avg)
                    row.append(
                        '{}-{}'.format(month_start.year, month_str))
                    row.append(visits_count)
                    row.append(leads_count)

                    csv_writer.writerow(row)
