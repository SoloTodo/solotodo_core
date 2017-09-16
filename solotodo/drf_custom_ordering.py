from rest_framework.filters import OrderingFilter


class CustomProductOrderingFilter(OrderingFilter):

    allowed_custom_filters = ['id', 'name', 'category', 'creation_date',
                              'last_updated']

    def get_valid_fields(self, queryset, view, context={}):
        return [(item, item) for item in self.allowed_custom_filters]

    def filter_queryset(self, request, queryset, view):

        ordering = self.get_ordering(request, queryset, view)
        new_ordering = []
        if ordering:
            # implement a custom ordering here
            for order in ordering:
                new_order = order

                if order in ['name', '-name']:
                    new_order = order.replace(
                        'name', 'instance_model__unicode_value')

                if order in ['category', '-category']:
                    new_order = order.replace(
                        'category', 'instance_model__model__category')

                new_ordering.append(new_order)

        if new_ordering:
            return queryset.order_by(*new_ordering)

        return queryset