class LgPricingDbRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'lg_pricing':
            return 'lg_pricing'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'lg_pricing':
            return 'lg_pricing'
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'lg_pricing':
            return db == 'lg_pricing'
        return None
