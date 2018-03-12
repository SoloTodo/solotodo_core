import metamodel.plugin


class MetaModelPlugin(metamodel.plugin.Plugin):
    @classmethod
    def on_instance_model_detail_view(cls, instance_model):
        from solotodo.models import Product
        try:
            product = Product.objects.get(instance_model=instance_model)
            product_link = u'<a class="btn btn-primary" ' \
                           u'href="https://www.solotodo.com/products/{}">' \
                           u'Ver ficha de producto</a>' \
                           u''.format(product.id)

            return u'<div class="btn-toolbar" role="toolbar">' \
                   u'<div class="btn-group" role="group">{}</div>' \
                   u'</div>'.format(product_link)
        except Product.DoesNotExist:
            return None
