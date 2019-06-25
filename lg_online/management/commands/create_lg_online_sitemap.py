import json
import xml.etree.ElementTree as ET

from django.core.management import BaseCommand
from django.utils import timezone

from solotodo.models import Product


class Command(BaseCommand):
    def handle(self, *args, **options):
        f = open('lg_online/products.json')
        product_entries = json.loads(f.read())
        f.close()

        urlset = ET.Element('urlset')
        urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')

        # Products

        for product_entry in product_entries:
            try:
                product = Product.objects.get(pk=product_entry['productId'])
            except Product.DoesNotExist:
                continue

            url = ET.SubElement(urlset, 'url')
            loc = ET.SubElement(url, 'loc')
            loc.text = 'https://www.lgonline.cl/products/{}-{}'.format(
                product.id, product.slug
            )
            lastmod = ET.SubElement(url, 'lastmod')
            lastmod.text = product.last_updated.isoformat()

            et = ET.ElementTree(urlset)
            file = open('lg_online_sitemap_products.xml', 'wb')
            et.write(file, encoding='utf-8', xml_declaration=True)
            file.close()

        # Categories

        urlset = ET.Element('urlset')
        urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')

        categories = [
            'televisores', 'refrigeradores', 'lavadoras', 'microondas',
            'celulares', 'audio', 'monitores', 'proyectores'
        ]

        for category in categories:
            url = ET.SubElement(urlset, 'url')
            loc = ET.SubElement(url, 'loc')
            loc.text = 'https://www.lgonline.cl/{}'.format(category)

        subcategories = [
            'televisores_hd', 'televisores_full_hd', 'televisores_ultra_hd_4k',
            'televisores_super_uhd_4k', 'televisores_oled_4k',
            'refrigeradores_top_freezer', 'refrigeradores_bottom_freezer',
            'refrigeradores_side_by_side', 'refrigeradores_french_door',
            'refrigeradores_door_in_door', 'lavadoras_carga_frontal',
            'lavadoras_carga_superior', 'lavadoras_y_secadoras',
            'secadoras', 'lavadoras_twinwash', 'lavadoras_twinwash_mini',
            'minicomponentes', 'microcomponentes', 'soundbars',
            'parlantes_portatiles_bluetooth', 'home_theaters',
            'monitores_gamer', 'monitores_profesionales', 'monitores_ultawide',
            'monitores_casa_y_oficina'
        ]

        for subcategory in subcategories:
            url = ET.SubElement(urlset, 'url')
            loc = ET.SubElement(url, 'loc')
            loc.text = 'https://www.lgonline.cl/{}'.format(subcategory)

        et = ET.ElementTree(urlset)
        file = open('lg_online_sitemap_others.xml', 'wb')
        et.write(file, encoding='utf-8', xml_declaration=True)
        file.close()

        # Sitemap index

        sitemapindex = ET.Element('sitemapindex')
        sitemapindex.set('xmlns',
                         'http://www.sitemaps.org/schemas/sitemap/0.9')

        sitemap = ET.SubElement(sitemapindex, 'sitemap')
        loc = ET.SubElement(sitemap, 'loc')
        loc.text = 'https://www.lgonline.cl/lg_online_sitemap_products.xml'
        lastmod = ET.SubElement(sitemap, 'lastmod')
        lastmod.text = timezone.now().isoformat()

        sitemap = ET.SubElement(sitemapindex, 'sitemap')
        loc = ET.SubElement(sitemap, 'loc')
        lastmod = ET.SubElement(sitemap, 'lastmod')
        lastmod.text = timezone.now().isoformat()
        loc.text = 'https://www.lgonline.cl/lg_online_sitemap_others.xml'

        et = ET.ElementTree(sitemapindex)
        file = open('lg_online_sitemap.xml', 'wb')
        et.write(file, encoding='utf-8', xml_declaration=True)
        file.close()
