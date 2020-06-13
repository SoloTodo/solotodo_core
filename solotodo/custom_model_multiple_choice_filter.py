from django import forms
from django.db.models import Q
from django_filters import MultipleChoiceFilter
from django_filters.filters import QuerySetRequestMixin


class CustomMultipleChoiceFilter(MultipleChoiceFilter):
    def filter(self, qs, value):
        if not value:
            # Even though not a noop, no point filtering if empty.
            return qs

        if self.is_noop(qs, value):
            return qs

        if not self.conjoined:
            q = Q()

        field_name = self.field.to_field_name
        for v in set(value):
            predicate = self.get_filter_predicate(v, field_name)
            if self.conjoined:
                qs = self.get_method(qs)(**predicate)
            else:
                q |= Q(**predicate)

        if not self.conjoined:
            qs = self.get_method(qs)(q)

        return qs.distinct() if self.distinct else qs

    def get_filter_predicate(self, v, field_name):
        try:
            return {self.field_name: getattr(v, field_name)}
        except (AttributeError, TypeError):
            return {self.field_name: v}


class CustomModelMultipleChoiceFilter(
        QuerySetRequestMixin, CustomMultipleChoiceFilter):
    field_class = forms.ModelMultipleChoiceField
