from django.dispatch import Signal

product_saved = Signal(providing_args=['product', 'es_document'])
