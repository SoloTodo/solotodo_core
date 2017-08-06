from django.dispatch import Signal

instance_model_saved = \
    Signal(providing_args=['instance_model', 'created', 'creator_id'])
