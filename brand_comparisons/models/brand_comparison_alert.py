import io
import xlsxwriter

from django.db import models
from django.contrib.auth import get_user_model

from .brand_comparison import BrandComparison
from solotodo.models import Store, Entity, EntityHistory


class BrandComparisonAlert(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    brand_comparison = models.ForeignKey(
        BrandComparison, on_delete=models.CASCADE)
    stores = models.ManyToManyField(Store)
    last_check = models.DateTimeField()

    def check_for_changes(self):
        changed = False

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)
        worksheet = workbook.add_worksheet()

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10})

        headers = [
            'Producto',
            'Tienda',
            'P. normal anterior',
            'P. normal nuevo',
            'P. oferta anterior',
            'P. oferta nuevo',
            'Producto comparado',
            'P. normal',
            'P. oferta']

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1

        for segment in self.brand_comparison.segments.all():
            for row in segment.rows.all():
                for store in self.stores.all():
                    try:
                        entity_1 = Entity.objects.get(
                            store=store, product=row.product_1)
                    except Entity.DoesNotExist:
                        continue

                    try:
                        entity_2 = Entity.objects.get(
                            store=store, product=row.product_2)
                    except Entity.DoesNotExist:
                        entity_2 = None

                    prev_registry = EntityHistory.objects.get(
                        entity=entity_1,
                        timestamp_lte=self.last_check)

                    curr_registry = entity_1.active_registry

                    compare_registry = entity_2.active_registry

                    if prev_registry.offer_price != \
                            curr_registry.offer_price or \
                            prev_registry.normal_price != \
                            curr_registry.normal_price:
                        changed = True
                        col = 0
                        worksheet.write(row, col, str(entity_1.product))
                        col += 1
                        worksheet.write(row, col, str(store))

    class Meta:
        app_label = 'brand_comparisons'
        ordering = ('user',)
