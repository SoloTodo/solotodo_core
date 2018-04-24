import re
import urllib
from urllib.parse import parse_qs

from django import forms

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
            sku = str(int(url.path.split('-')[-1][:-1]))
        elif url.netloc == 'www.paris.cl':
            store = Store.objects.get(name='Paris')
            sku = re.search(r'-(\d{6,7})-', url.path).groups()[0]
        elif url.netloc == 'www.abcdin.cl':
            store = Store.objects.get(name='AbcDin')
            if "productId" in url.path:
                sku = 'productId=' + parse_qs(url.query)['productId'][0]
            else:
                sku = re.search(r'-(\d{6,7})', url.path).groups()[0]
        elif url.netloc == 'www.lapolar.cl':
            store = Store.objects.get(name='La Polar')
            sku = re.findall('(\d+)', url.path)[-1]
        elif url.netloc == 'www.pcfactory.cl':
            store = Store.objects.get(name='PCFactory')
            sku = re.findall('(\d+)', url.path)[0] + '-'
        elif url.netloc == 'www.corona.cl':
            store = Store.objects.get(name='Corona')
            sku = url.path
        elif url.netloc == 'www.linio.cl':
            store = Store.objects.get(name='Linio Chile')
            sku = url.path
        elif url.netloc == 'www.bip.cl':
            store = Store.objects.get(name='Bip')
            sku = 'id_producto=' + parse_qs(url.query)['id_producto'][0]
        elif url.netloc == 'www.hponline.cl':
            store = Store.objects.get(name='HP Online')
            sku = url.path
        elif url.netloc == 'www.infor-ingen.com':
            store = Store.objects.get(name='Infor-Ingen')
            sku = 'product_id={}&'.format(
                parse_qs(url.query)['product_id'][0])
        elif url.netloc == 'www.maconline.cl' \
                or url.netloc == 'www.maconline.com':
            store = Store.objects.get(name='MacOnline')
            if 'producto' in url.path:
                sku = url.path
            else:
                raise Exception
        elif url.netloc == 'www.magens.cl':
            store = Store.objects.get(name='Magens')
            sku = url.path
        elif url.netloc == 'www.pc-express.cl':
            store = Store.objects.get(name='PC Express')
            sku = 'products_id=' + parse_qs(url.query)['products_id'][0]
        elif url.netloc == 'www.pcofertas.cl':
            store = Store.objects.get(name='PC Ofertas')
            sku = url.path
        elif url.netloc == 'www.peta.cl':
            store = Store.objects.get(name='Peta')
            sku = url.path
        elif url.netloc == 'www.reifstore.cl':
            store = Store.objects.get(name='Reifschneider')
            sku = url.path.split('/')[-1]
        elif url.netloc == 'www.sistemax.cl':
            store = Store.objects.get(name='Sistemax')
            sku = 'product_id=' + parse_qs(url.query)['product_id'][0]
        elif url.netloc == 'www.ttchile.cl':
            store = Store.objects.get(name='TtChile')
            if url.path != '/producto.php':
                raise Exception
            sku = 'i=' + parse_qs(url.query)['i'][0]
        elif url.netloc == 'www.wei.cl':
            store = Store.objects.get(name='Wei')
            sku = 'pcode=' + parse_qs(url.query)['pcode'][0]
        elif url.netloc == 'www.samsungonline.cl':
            store = Store.objects.get(name='Samsung Online')
            sku = url.path
        elif url.netloc == 'www.easy.cl':
            store = Store.objects.get(name='Easy')
            sku = re.search(r'-(\d{6,7})', url.path).groups()[0]
        elif url.netloc == 'www.globalmac.cl':
            store = Store.objects.get(name='GlobalMac')
            sku = url.path
        elif url.netloc == 'www.hites.com':
            store = Store.objects.get(name='Hites')
            sku = 'productId=' + parse_qs(url.query)['productId'][0]
        elif url.netloc == 'www.lider.cl':
            store = Store.objects.get(name='Lider')
            sku = 'productId=' + parse_qs(url.query)['productId'][0]
        elif url.netloc == 'blackfriday.lider.cl':
            store = Store.objects.get(name='Lider')
            sku = re.search(r'(PROD_.+)', url.fragment).groups()[0]
        elif url.netloc == 'www.netnow.cl':
            store = Store.objects.get(name='NetNow')
            sku = url.path
        elif url.netloc == 'www.samsungstore.cl':
            store = Store.objects.get(name='Samsung Store')
            sku = url.path
        elif url.netloc == 'www.sodimac.cl':
            store = Store.objects.get(name='Sodimac')
            sku = url.path
        elif url.netloc == 'store.sony.cl':
            store = Store.objects.get(name='SonyStyle')
            sku = url.path
        elif url.netloc == 'www.spdigital.cl':
            store = Store.objects.get(name='SpDigital')
            sku = url.path
        else:
            return None

        entities = Entity.objects.filter(
            store=store,
            sku=sku
        ).order_by('-id')

        if not entities:
            return None

        return entities[0]
