from rest_framework.pagination import PageNumberPagination


class StoreUpdateLogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class EntityPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProductPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 100


class EntityPriceHistoryPagination(PageNumberPagination):
    page_size = 1000
