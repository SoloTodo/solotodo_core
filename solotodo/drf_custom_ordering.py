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
                        'name', 'instance_model')

                if order in ['category', '-category']:
                    new_order = order.replace(
                        'category', 'instance_model__model__category')

                new_ordering.append(new_order)

        if new_ordering:
            return queryset.order_by(*new_ordering)

        return queryset


class CustomEntityOrderingFilter(OrderingFilter):

    allowed_custom_filters = ['id', 'name', 'store', 'sku', 'category',
                              'product', 'cell_plan', 'normal_price',
                              'offer_price', 'creation_date', 'last_updated',
                              'last_association', 'last_staff_access',
                              'last_staff_change', 'last_pricing_update']

    def get_valid_fields(self, queryset, view, context={}):
        return [(item, item) for item in self.allowed_custom_filters]

    def filter_queryset(self, request, queryset, view):

        ordering = self.get_ordering(request, queryset, view)
        new_ordering = []
        if ordering:
            # implement a custom ordering here
            for order in ordering:
                new_order = order

                if order in ['normal_price', '-normal_price']:
                    new_order = order.replace(
                        'normal_price', 'active_registry__normal_price')

                if order in ['offer_price', '-offer_price']:
                    new_order = order.replace(
                        'normal_price', 'active_registry__offer_price')

                new_ordering.append(new_order)

        if new_ordering:
            return queryset.order_by(*new_ordering)

        return queryset
