class CacheControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if '/metamodel/' in request.path:
            response['Cache-Control'] = 'no-cache'

        return response
