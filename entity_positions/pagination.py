from rest_framework.pagination import PageNumberPagination


class EntityPositionPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 150
