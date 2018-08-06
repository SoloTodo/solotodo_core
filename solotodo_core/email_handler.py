from django.utils.log import AdminEmailHandler
from django.core.cache import cache


class ThrottledAdminEmailHandler(AdminEmailHandler):
    PERIOD_LENGTH_IN_SECONDS = 86400
    MAX_EMAILS_IN_PERIOD = 50
    COUNTER_CACHE_KEY = 'email_admins_counter'

    def increment_counter(self):
        try:
            cache.incr(self.COUNTER_CACHE_KEY)
        except ValueError:
            cache.set(self.COUNTER_CACHE_KEY, 1,
                      self.PERIOD_LENGTH_IN_SECONDS)
        return cache.get(self.COUNTER_CACHE_KEY)

    def emit(self, record):
        try:
            counter = self.increment_counter()
        except Exception:
            pass
        else:
            if counter > self.MAX_EMAILS_IN_PERIOD:
                return

        super(ThrottledAdminEmailHandler, self).emit(record)
