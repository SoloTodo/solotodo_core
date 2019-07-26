import io
import xlsxwriter

from django import forms
from django.utils import timezone
from django.core.files.base import ContentFile
from guardian.shortcuts import get_objects_for_user

from solotodo.filter_utils import IsoDateTimeRangeField
from solotodo.models import Website, Store, Category
from soicos_conversions.models import SoicosConversion
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportSoicosConversions(forms.Form):
    timestamp = IsoDateTimeRangeField()
    sites = forms.ModelMultipleChoiceField(
        queryset=Website.objects.all(), required=False)
    stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all(), required=False)
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(), required=False)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        valid_categories = get_objects_for_user(user, 'view_category_reports',
                                                Category)
        self.fields['categories'].queryset = valid_categories

        valid_stores = get_objects_for_user(user, 'view_store_reports', Store)
        self.fields['stores'].queryset = valid_stores

    def clean_stores(self):
        selected_stores = self.cleaned_data['stores']
        if selected_stores:
            return selected_stores
        else:
            return self.fields['stores'].queryset

    def clean_categories(self):
        selected_categories = self.cleaned_data['categories']
        if selected_categories:
            return selected_categories
        else:
            return self.fields['categories'].queryset

    def clean_sites(self):
        selected_sites = self.cleaned_data['sites']
        if selected_sites:
            return selected_sites
        else:
            return self.fields['sites'].queryset

    def generate_report(self):
        categories = self.cleaned_data['categories']
        sites = self.cleaned_data['sites']
        stores = self.cleaned_data['stores']
        timestamp = self.cleaned_data['timestamp']

        conversions = SoicosConversion.objects.filter(
            lead__entity_history__entity__category__in=categories,
            lead__entity_history__entity__store__in=stores,
            lead__website__in=sites,
            creation_date__gte=timestamp.start,
            creation_date__lte=timestamp.stop
        )

        status_dict = {
            1: 'OK',
            2: 'Cancelado',
            3: 'Pendiente',
            4: 'Bloqueado',
            5: 'País Invalido'}

        # REPORT CREATION "
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)
        worksheet = workbook.add_worksheet()

        url_format = workbook.add_format({
            'font_color': 'blue',
            'font_size': 10
        })

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10
        })

        date_format = workbook.add_format({
            'num_format': 'yyyy-mm-dd',
            'font_size': 10
        })

        headers = [
            "Producto",
            "Categoría",
            "Tienda",
            "SKU",
            "Precio Normal",
            "Precio Oferta",
            "UUID",
            "Fecha Lead",
            "Website",
            "Id transacción",
            "Estado",
            "Fecha creacion conversión",
            "Fecha validación conversion",
            "Payout",
            "Transaction Total"
        ]

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1
        for conversion in conversions:
            col = 0
            worksheet.write_url(
                row, col,
                conversion.lead.entity_history.entity.url,
                string=str(conversion.lead.entity_history.entity.product),
                cell_format=url_format
            )

            col += 1
            worksheet.write(
                row, col, str(conversion.lead.entity_history.entity.category))

            col += 1
            worksheet.write(
                row, col, str(conversion.lead.entity_history.entity.store))

            col += 1
            worksheet.write(
                row, col, conversion.lead.entity_history.entity.sku)

            col += 1
            worksheet.write(
                row, col, conversion.lead.entity_history.normal_price)

            col += 1
            worksheet.write(
                row, col, conversion.lead.entity_history.offer_price)

            col += 1
            worksheet.write(
                row, col, conversion.lead.uuid)

            col += 1
            worksheet.write(
                row, col, conversion.lead.timestamp.date(), date_format)

            col += 1
            worksheet.write(
                row, col, str(conversion.lead.website))

            col += 1
            worksheet.write(
                row, col, conversion.transaction_id)

            col += 1
            worksheet.write(
                row, col, status_dict[conversion.status])

            col += 1
            worksheet.write(
                row, col, conversion.creation_date.date(), date_format)

            col += 1
            if conversion.validation_date:
                worksheet.write(
                    row, col, conversion.validation_date.date(), date_format)
            else:
                worksheet.write(
                    row, col, 'Sin validar')

            col += 1
            worksheet.write(
                row, col, conversion.payout)

            col += 1
            worksheet.write(
                row, col, conversion.transaction_total)

            row += 1

        worksheet.autofilter(0, 0, row - 1, len(headers) - 1)
        workbook.close()

        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()

        filename_template = 'soicos_conversions_%Y-%m-%d_%H:%M:%S'

        filename = timezone.now().strftime(filename_template)

        path = storage.save('reports/{}.xlsx'.format(filename),
                            file_for_upload)

        return {
            'file': file_value,
            'path': path
        }
