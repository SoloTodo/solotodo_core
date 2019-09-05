from django.db import models
from django.core.mail import EmailMessage
from django.contrib.auth import get_user_model

from solotodo_core.settings import ADMINS
from solotodo.models import Store, Category, Entity, SoloTodoUser


class KeywordSearch(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    keyword = models.CharField(max_length=512)
    threshold = models.IntegerField()
    creation_date = models.DateTimeField(auto_now_add=True)
    active_update = models.ForeignKey(
        'KeywordSearchUpdate', null=True, blank=True,
        on_delete=models.CASCADE)

    def __str__(self):
        return '{} - {} - {} - {}'.format(
            self.user,
            self.store,
            self.keyword,
            self.creation_date)

    def update(self, use_async=None):
        from .keyword_search_update import KeywordSearchUpdate
        from .keyword_search_entity_position import KeywordSearchEntityPosition

        update = KeywordSearchUpdate.objects.create(
            search=self,
            status=KeywordSearchUpdate.IN_PROCESS)

        self.active_update = update
        self.save()

        try:
            products = self.store.scraper.products_for_keyword(
                self.keyword,
                self.threshold,
                use_async=use_async)['products']
        except Exception as e:
            update.status = KeywordSearchUpdate.ERROR
            update.message = str(e)
            update.save()
            message = "Error al realizar búsqueda por keyword '{}' ({}) " \
                      "en tienda {}.\n ERROR: {}"\
                .format(self.keyword, self.id, self.store, str(e))
            self.send_keyword_mail(message)
            return

        if not products:
            self.send_keyword_mail(
                "No se encontraron productos "
                "para el keyword '{}' ({}) en la tienda {}."
                .format(self.keyword, self.id, self.store))

        for idx, product in enumerate(products):
            try:
                entity = Entity.objects.get(store=self.store, key=product.key)

                KeywordSearchEntityPosition.objects.create(
                    entity=entity,
                    update=update,
                    value=idx+1)

            except Entity.DoesNotExist:
                continue

        update.status = KeywordSearchUpdate.SUCCESS
        update.save()

    def send_keyword_mail(self, message):
        sender = SoloTodoUser.get_bot().email_recipient_text()
        subject = 'Actualización Keyword Search {} ({})'\
            .format(self.store, self.category)
        recipients = []

        for admin in ADMINS:
            recipients.append(admin[1])

        email = EmailMessage(subject, message, sender, recipients)
        email.send()

    def save(self, *args, **kwargs):
        from keyword_search_positions.tasks import keyword_search_update
        should_update = not self.id
        super(KeywordSearch, self).save(*args, **kwargs)

        if should_update:
            keyword_search_update.delay(self.id)

    class Meta:
        app_label = 'keyword_search_positions'
        ordering = ('-creation_date',)
        permissions = (
            ['backend_list_keyword_searches',
             'Can see keyword searches in the backend'],
        )
