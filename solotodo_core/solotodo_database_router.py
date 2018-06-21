class SoloTodoDatabaseRouter(object):
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'analytics':
            return 'analytics'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'analytics':
            return 'analytics'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.app_label == 'analytics' or \
           obj2._meta.app_label == 'analytics':
           return True
        return None

    def allow_migrate(self, db, app_label, model=None, **hints):
        if app_label == 'analytics':
            return False
        return None
