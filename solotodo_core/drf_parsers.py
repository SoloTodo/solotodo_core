import json

from rest_framework.parsers import BaseParser


class PlainTextJsonParser(BaseParser):
    media_type = 'text/plain'

    def parse(self, stream, media_type=None, parser_context=None):
        return json.loads(stream.read())
