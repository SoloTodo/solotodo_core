import re
import urllib
from urllib.parse import parse_qs

from django import forms
from django.db.models import Q

from solotodo.models import Store, Entity


class EntityByUrlForm(forms.Form):
    url = forms.URLField()

    def get_entity(self):
        url = urllib.parse.urlparse(self.cleaned_data['url'])

        if url.netloc == 'www.falabella.com':
            store = Store.objects.get(name='Falabella')
            m = re.search('/product/(\d+)', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'simple.ripley.cl':
            store = Store.objects.get(name='Ripley')
            m = re.search('(\d+)p', url.path)
            if not m:
                m = re.search('mpm(\d+)', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.paris.cl':
            store = Store.objects.get(name='Paris')
            m = re.search('(\d+)-ppp', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.abcdin.cl':
            store = Store.objects.get(name='AbcDin')
            if 'productId' in url.path:
                sku = 'productId=' + parse_qs(url.query)['productId'][0]
            else:
                m = re.search(r'-(\d{6,7})', url.path)
                if not m:
                    return None
                sku = m.groups()[0]
        elif url.netloc == 'tienda.lapolar.cl':
            store = Store.objects.get(name='La Polar')
            m = re.search(r'/(\d{8})', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.pcfactory.cl':
            store = Store.objects.get(name='PC Factory')
            m = re.search(r'producto/(\d+)', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.corona.cl':
            store = Store.objects.get(name='Corona')
            m = re.search(r'(.+)/p$', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.linio.cl':
            store = Store.objects.get(name='Linio Chile')
            m = re.search(r'-([a-zA-Z0-9]+)$', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.bip.cl':
            store = Store.objects.get(name='Bip')
            parsed_qs = parse_qs(url.query)
            if 'id_producto' in parsed_qs:
                sku = parsed_qs['id_producto'][0]
            else:
                return None
        elif url.netloc == 'www.hponline.cl':
            store = Store.objects.get(name='HP Online')
            m = re.search(r'-([a-zA-Z0-9]+)$', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.infor-ingen.com':
            store = Store.objects.get(name='Infor-Ingen')
            parsed_qs = parse_qs(url.query)
            if 'product_id' in parsed_qs:
                sku = parsed_qs['product_id'][0]
            else:
                return None
        elif url.netloc == 'www.magens.cl':
            store = Store.objects.get(name='Magens')
            m = re.search(r'-p-(\d+)$', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'tienda.pc-express.cl':
            store = Store.objects.get(name='PC Express')
            parsed_qs = parse_qs(url.query)
            if 'product_id' in parsed_qs:
                sku = parsed_qs['product_id'][0]
            else:
                return None
        elif url.netloc == 'www.reifstore.cl':
            store = Store.objects.get(name='Reifschneider')
            m = re.search(r'/(\d+)-', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.sistemax.cl':
            store = Store.objects.get(name='Sistemax')
            parsed_qs = parse_qs(url.query)
            if 'product_id' in parsed_qs:
                sku = 'product_id=' + parsed_qs['product_id'][0]
            else:
                return None
        elif url.netloc == 'www.ttchile.cl':
            store = Store.objects.get(name='TtChile')
            parsed_qs = parse_qs(url.query)
            if 'i' in parsed_qs:
                sku = parsed_qs['i'][0]
            else:
                return None
        elif url.netloc == 'www.wei.cl':
            store = Store.objects.get(name='Wei')
            m = re.search(r'producto/(.+)$', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.tiendasmart.cl':
            store = Store.objects.get(name='Tienda Smart')
            sku = url.path
        elif url.netloc == 'www.easy.cl':
            store = Store.objects.get(name='Easy')
            m = re.search('(\d+)p$', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.hites.com':
            store = Store.objects.get(name='Hites')
            sku = url.path.split('/')[-1]
        elif url.netloc == 'www.lider.cl':
            store = Store.objects.get(name='Lider')
            m = re.search('/(\d+)$', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.netnow.cl':
            store = Store.objects.get(name='NetNow')
            m = re.search('/\d+-.+/(\d+)-', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.vivelo.cl':
            store = Store.objects.get(name='Vivelo')
            sku = url.path
        elif url.netloc == 'www.sodimac.cl':
            store = Store.objects.get(name='Sodimac')
            m = re.search('/product/(\d+)', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'store.sony.cl':
            store = Store.objects.get(name='Sony Store')
            m = re.search('(.+)/p$', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.spdigital.cl':
            store = Store.objects.get(name='SpDigital')
            m = re.search('products/view/(\d+)$', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.winpy.cl':
            store = Store.objects.get(name='Winpy')
            m = re.search('/venta/(.+)$', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        else:
            return None

        sku_filter = Q(store=store) & (Q(url__icontains=sku) |
                                       Q(sku__icontains=sku))
        entities = Entity.objects.filter(sku_filter).order_by('-id')

        if not entities:
            return None

        return entities[0]
