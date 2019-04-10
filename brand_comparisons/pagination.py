from rest_framework.pagination import PageNumberPagination


class BrandComparisonPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 50
