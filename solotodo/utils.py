import collections


def iterable_to_dict(iterable_or_model, field):
    if not isinstance(iterable_or_model, collections.Iterable):
        iterable_or_model = iterable_or_model.objects.all()

    return {getattr(e, field): e for e in iterable_or_model}
