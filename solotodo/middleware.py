class CacheControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if 'HTTP_AUTHORIZATION' in request.META:
            response['Cache-Control'] = 'no-cache'

        return response


class CrawlerMiddleware:
    BOT_NAMES = ['Googlebot', 'Slurp', 'Twiceler', 'msnbot', 'KaloogaBot',
                 'YodaoBot', '"Baiduspider', 'googlebot', 'Speedy Spider',
                 'DotBot']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        request.is_crawler = False

        for botname in self.BOT_NAMES:
            if botname in user_agent:
                request.is_crawler = True
                break

        response = self.get_response(request)

        return response
