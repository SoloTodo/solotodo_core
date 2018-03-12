from django.conf import settings
from elasticsearch_dsl import Search
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


class NotebookProcessorViewSet(ViewSet):
    def list(self, request, *args, **kwargs):
        search = Search(using=settings.ES, index='notebook-processors')
        response = search[:1000].execute()
        serialized_result = [
            e['_source'] for e in response.to_dict()['hits']['hits']]
        return Response(serialized_result)


class NotebookVideoCardViewSet(ViewSet):
    def list(self, request, *args, **kwargs):
        search = Search(using=settings.ES, index='notebook-video-cards')
        response = search[:1000].execute()
        serialized_result = [
            e['_source'] for e in response.to_dict()['hits']['hits']]
        return Response(serialized_result)
