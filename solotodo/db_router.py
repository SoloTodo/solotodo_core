import random


class RdsDbRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'metamodel':
            return 'writer'
        if model._meta.app_label != 'lg_pricing':
            if random.random() <= 0.7:
                return 'reader'
            else:
                return 'writer'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label != 'lg_pricing':
            return 'writer'
        else:
            return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._state.db in ['default', 'reader', 'writer'] and \
                obj2._state.db in ['default', 'reader', 'writer']:
            return True
        else:
            return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label != 'lg_pricing':
            if db == 'writer':
                return True
            elif db == 'reader':
                return False
        return None
