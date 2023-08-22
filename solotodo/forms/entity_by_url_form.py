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
            m = re.search(r'/product/\d+/.+/(\d+)', url.path)
            if not m:
                m = re.search(r'/product/(\d+)/', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'simple.ripley.cl':
            store = Store.objects.get(name='Ripley')
            m = re.search(r'(\d+)p', url.path)
            if not m:
                store = Store.objects.get(name='Mercado Ripley')
                m = re.search(r'mpm(\d+)', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.paris.cl':
            store = Store.objects.get(name='Paris')
            m = re.search(r'(\d+)(ppp|PPP|999)\.html', url.path)
            if not m:
                return None
            sku = m.groups()[0] + m.groups()[1]
        elif url.netloc == 'www.abcdin.cl':
            store = Store.objects.get(name='AbcDin')
            if 'productId' in url.path:
                sku = 'productId=' + parse_qs(url.query)['productId'][0]
            else:
                m = re.search(r'-(\d{6,7})', url.path)
                if not m:
                    return None
                sku = m.groups()[0]
        elif url.netloc == 'www.lapolar.cl':
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
            store = Store.objects.get(name='ReifStore')
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
            store = Store.objects.get(name='TyT Chile')
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
            m = re.search(r'(\d+)p$', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.hites.com':
            store = Store.objects.get(name='Hites')
            m = re.search(r'(\d+)$', url.path)
            if not m:
                return None
            sku = m.groups()[0][:-3]
        elif url.netloc == 'www.lider.cl':
            store = Store.objects.get(name='Lider')
            m = re.search(r'/(\d+)$', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.netnow.cl':
            store = Store.objects.get(name='NetNow')
            m = re.search(r'/\d+-.+/(\d+)-', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'www.vivelo.cl':
            store = Store.objects.get(name='Vivelo')
            sku = url.path
        elif url.netloc == 'www.sodimac.cl':
            store = Store.objects.get(name='Sodimac')
            m = re.search(r'/product/(\d+)', url.path)
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
            store = Store.objects.get(name='SP Digital')
            m = re.search(r'products/view/(\d+)$', url.path)
            if not m:
                m = re.search(r'products/cyberday_view/(\d+)$', url.path)
            if not m:
                return None
            sku = m.groups()[0]
        elif url.netloc == 'cyber.cloud.spdigital.cl':
            store = Store.objects.get(name='SpDigital')
            m = re.search(r'id=(\d+)$', url.query)
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

        entities = Entity.objects.filter(store=store)

        sku_entities = entities.filter(Q(sku__icontains=sku) |
                                       Q(key__icontains=sku))

        if not sku_entities:
            sku_entities = entities.filter(url__icontains=sku)

        sku_entities = sku_entities.order_by('-id')

        if not sku_entities:
            return None

        return sku_entities[0]
