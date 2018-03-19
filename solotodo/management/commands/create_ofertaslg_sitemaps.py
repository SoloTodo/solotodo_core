import xml.etree.ElementTree as ET

from django.contrib.auth.models import Group
from django.core.management import BaseCommand
from django.utils import timezone
from guardian.shortcuts import get_objects_for_group

from metamodel.models import MetaModel
from solotodo.models import Product, Category


class Command(BaseCommand):
    def handle(self, *args, **options):
        group = Group.objects.get(name='base')
        categories = get_objects_for_group(group, 'view_category', Category)

        search = Product.es_search().filter('term', brand_name='lg')
        es_results = search[:100000].execute()

        product_ids = [e.product_id for e in es_results]
        all_products = list(Product.objects.filter(pk__in=product_ids)
                            .filter_by_category(categories)
                            .select_related('instance_model'))

        # Products

        step = 50000
        page = 0

        while True:
            products = all_products[step*page:step*(page + 1)]
            if not products:
                break

            urlset = ET.Element('urlset')
            urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')

            for product in products:
                url = ET.SubElement(urlset, 'url')
                loc = ET.SubElement(url, 'loc')
                loc.text = 'https://www.ofertaslg.cl/products/{}-{}'.format(
                    product.id, product.slug
                )
                lastmod = ET.SubElement(url, 'lastmod')
                lastmod.text = product.last_updated.isoformat()

            et = ET.ElementTree(urlset)
            file = open('ofertaslg_sitemap_products_{}.xml'.format(page + 1),
                        'wb')
            et.write(file, encoding='utf-8', xml_declaration=True)
            file.close()

            page += 1

        # Categories and others

        categories = Category.objects.filter(
            pk__in=[1, 11, 26, 6, 14, 15, 17, 18, 19, 4, 25, 27, 28, 29, 31,
                    36, 37, 46])

        urlset = ET.Element('urlset')
        urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')

        for category in categories:
            url = ET.SubElement(urlset, 'url')
            loc = ET.SubElement(url, 'loc')
            loc.text = 'https://www.ofertaslg.cl/{}'.format(category.slug)

        et = ET.ElementTree(urlset)
        file = open('ofertaslg_sitemap_others.xml', 'wb')
        et.write(file, encoding='utf-8', xml_declaration=True)
        file.close()

        # Sitemap index

        sitemapindex = ET.Element('sitemapindex')
        sitemapindex.set('xmlns',
                         'http://www.sitemaps.org/schemas/sitemap/0.9')

        for local_page in range(page):
            sitemap = ET.SubElement(sitemapindex, 'sitemap')
            loc = ET.SubElement(sitemap, 'loc')
            loc.text = 'https://www.ofertaslg.cl/' \
                       'ofertaslg_sitemap_products_{}.xml' \
                       ''.format(local_page + 1)
            lastmod = ET.SubElement(sitemap, 'lastmod')
            lastmod.text = timezone.now().isoformat()

        sitemap = ET.SubElement(sitemapindex, 'sitemap')
        loc = ET.SubElement(sitemap, 'loc')
        lastmod = ET.SubElement(sitemap, 'lastmod')
        lastmod.text = timezone.now().isoformat()
        loc.text = 'https://www.ofertaslg.cl/ofertaslg_sitemap_others.xml'

        et = ET.ElementTree(sitemapindex)
        file = open('ofertaslg_sitemap.xml', 'wb')
        et.write(file, encoding='utf-8', xml_declaration=True)
        file.close()
