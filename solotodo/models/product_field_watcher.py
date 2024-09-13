from django.db import models

from .category import Category


class ProductFieldWatcher(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    es_label_path = models.CharField(max_length=255)
    es_value_path = models.CharField(max_length=255)
    es_instance_model_id_path = models.CharField(max_length=255)
    es_target_value = models.IntegerField()

    def __str__(self):
        return "{} - {}".format(self.category, self.name)

    class Meta:
        app_label = "solotodo"
        ordering = ("category", "name")
