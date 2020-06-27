import xml.etree.ElementTree as ET

from django.contrib.auth.models import Group
from django.core.management import BaseCommand
from django.utils import timezone
from guardian.shortcuts import get_objects_for_group

from metamodel.models import MetaModel
from solotodo.models import Product, Category


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('country_code', type=str, nargs=1)

    def handle(self, *args, **options):
        domains_dict = {
            'cl': 'https://www.solotodo.cl',
            'mx': 'https://www.solotodo.com.mx',
        }

        country_code = options['country_code'][0].lower()
        domain = domains_dict[country_code]

        group = Group.objects.get(name='base')
        categories = get_objects_for_group(group, 'view_category', Category)

        # Products

        step = 20000
        page = 0

        while True:
            products = Product.objects\
                .filter_by_category(categories)\
                .select_related('instance_model')[step*page:step*(page + 1)]
            if not products:
                break

            urlset = ET.Element('urlset')
            urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')

            for product in products:
                url = ET.SubElement(urlset, 'url')
                loc = ET.SubElement(url, 'loc')
                loc.text = '{}/products/{}-{}'.format(
                    domain, product.id, product.slug
                )
                lastmod = ET.SubElement(url, 'lastmod')
                lastmod.text = product.last_updated.isoformat()

            et = ET.ElementTree(urlset)
            file = open('sitemap_products_{}_{}.xml'.format(
                page + 1, country_code), 'wb')
            et.write(file, encoding='utf-8', xml_declaration=True)
            file.close()

            page += 1

        # Categories and others

        urlset = ET.Element('urlset')
        urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')

        for category in categories:
            url = ET.SubElement(urlset, 'url')
            loc = ET.SubElement(url, 'loc')
            loc.text = '{}/{}'.format(domain, category.slug)

        # Notebook processors

        url = ET.SubElement(urlset, 'url')
        loc = ET.SubElement(url, 'loc')
        loc.text = '{}/notebook_processors'.format(domain)

        model = MetaModel.objects.get(name='NotebookProcessor')

        for notebook_processor in model.instancemodel_set.all():
            url = ET.SubElement(urlset, 'url')
            loc = ET.SubElement(url, 'loc')
            loc.text = '{}/notebook_processors?id={}'.format(
                domain, notebook_processor.id)

        # Notebook video cards

        url = ET.SubElement(urlset, 'url')
        loc = ET.SubElement(url, 'loc')
        loc.text = '{}/notebook_video_cards'.format(domain)

        model = MetaModel.objects.get(name='NotebookVideoCard')

        for notebook_video_card in model.instancemodel_set.all():
            url = ET.SubElement(urlset, 'url')
            loc = ET.SubElement(url, 'loc')
            loc.text = '{}/notebook_video_cards?id={}'.format(
                domain, notebook_video_card.id)

        # Video card GPUs

        model = MetaModel.objects.get(name='VideoCardGpu')

        for video_card_gpu in model.instancemodel_set.all():
            url = ET.SubElement(urlset, 'url')
            loc = ET.SubElement(url, 'loc')
            loc.text = '{}/video_card_gpus/{}'.format(
                domain, video_card_gpu.id)

        et = ET.ElementTree(urlset)
        file = open('sitemap_others_{}.xml'.format(country_code), 'wb')
        et.write(file, encoding='utf-8', xml_declaration=True)
        file.close()

        # Sitemap index

        sitemapindex = ET.Element('sitemapindex')
        sitemapindex.set('xmlns',
                         'http://www.sitemaps.org/schemas/sitemap/0.9')

        for local_page in range(page):
            sitemap = ET.SubElement(sitemapindex, 'sitemap')
            loc = ET.SubElement(sitemap, 'loc')
            loc.text = 'https://solotodo-core.s3.amazonaws.com/sitemaps/' \
                       'sitemap_products_{}_{}.xml'.format(
                        local_page + 1, country_code)
            lastmod = ET.SubElement(sitemap, 'lastmod')
            lastmod.text = timezone.now().isoformat()

        sitemap = ET.SubElement(sitemapindex, 'sitemap')
        loc = ET.SubElement(sitemap, 'loc')
        lastmod = ET.SubElement(sitemap, 'lastmod')
        lastmod.text = timezone.now().isoformat()
        loc.text = 'https://solotodo-core.s3.amazonaws.com/sitemaps/' \
                   'sitemap_others_{}.xml'.format(country_code)

        et = ET.ElementTree(sitemapindex)
        file = open('sitemap_{}.xml'.format(country_code), 'wb')
        et.write(file, encoding='utf-8', xml_declaration=True)
        file.close()
