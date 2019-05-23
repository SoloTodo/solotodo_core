from django.core.management import BaseCommand

from keyword_search_positions.models import KeywordSearch
from keyword_search_positions.tasks import keyword_search_update


class Command(BaseCommand):
    def handle(self, *args, **options):
        keyword_searches = KeywordSearch.objects.all()

        for keyword_search in keyword_searches:
            keyword_search_update.delay(keyword_search.id)
