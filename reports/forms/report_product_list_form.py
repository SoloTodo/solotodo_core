import io

import xlsxwriter
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django_filters.fields import IsoDateTimeRangeField
from guardian.shortcuts import get_objects_for_user

from category_columns.models import CategoryColumn
from solotodo.models import (
    Category,
    Product,
)
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportProductListForm(forms.Form):
    category = forms.ModelChoiceField(queryset=Category.objects.all())
    timestamp = IsoDateTimeRangeField()

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        valid_categories = get_objects_for_user(user, "view_category_reports", Category)
        self.fields["category"].queryset = valid_categories

    def generate_report(self):
        category = self.cleaned_data["category"]
        timestamp = self.cleaned_data["timestamp"]

        products = (
            Product.objects.filter_by_category(category)
            .filter(
                creation_date__gte=timestamp.start,
                creation_date__lte=timestamp.stop,
            )
            .order_by("instance_model__unicode_representation")
            .select_related("brand", "instance_model")
        )

        Product.prefetch_specs(products)

        specs_columns = CategoryColumn.objects.filter(
            field__category=category,
            purpose=settings.REPORTS_PURPOSE_ID,
            is_extended=False,
        ).select_related("field")

        output = io.BytesIO()

        # Create a workbook and add a worksheet
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        date_format = workbook.add_format({"num_format": "yyyy-mm-dd", "font_size": 10})
        worksheet = workbook.add_worksheet()
        header_format = workbook.add_format({"bold": True, "font_size": 10})
        headers = ["Identificador", "Nombre", "Marca", "Fecha de creación"]
        headers.extend([column.field.label for column in specs_columns])

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1

        for product in products:
            col = 0
            worksheet.write(row, col, product.id)
            col += 1
            worksheet.write(row, col, str(product))
            col += 1
            worksheet.write(row, col, str(product.brand))
            col += 1
            worksheet.write(row, col, str(product.creation_date.date()), date_format)
            col += 1

            for column in specs_columns:
                worksheet.write(
                    row, col, product.specs.get(column.field.es_field, "N/A")
                )
                col += 1

            row += 1

        worksheet.autofilter(0, 0, row - 1, len(headers) - 1)
        workbook.close()

        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()

        filename_template = "product_list_report_%Y-%m-%d_%H:%M:%S"
        filename = timezone.now().strftime(filename_template)
        path = storage.save("reports/{}.xlsx".format(filename), file_for_upload)

        return {"file": file_value, "path": path}
