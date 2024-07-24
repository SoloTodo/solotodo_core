import io
import json
import xlsxwriter


from django import forms
from django.core.files.base import ContentFile
from django.utils import timezone


from solotodo.models import Store
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportMercadoLibreChileCatalogForm(forms.Form):
    seller_id = forms.CharField(required=True)

    def generate_report(self):
        seller_id = self.cleaned_data["seller_id"]
        store = Store.objects.get(name="Mercado Libre")
        scraper = store.scraper
        scraper_extra_args = json.loads(store.storescraper_extra_args)
        preflight_data = scraper.preflight(scraper_extra_args)
        access_token = preflight_data["access_token"]
        scraped_data = scraper.get_catalog_competitors_for_seller(
            seller_id, access_token
        )

        output = io.BytesIO()

        # Create a workbook and add a worksheet.
        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)
        worksheet = workbook.add_worksheet()

        header_format = workbook.add_format({"bold": True, "font_size": 10})

        headers = [
            "ID Producto",
            "Nombre Producto",
            "URL Producto",
            "ID Dreamtec",
            "Precio Dreamtec",
            "¿Oferta ganadora?",
            "Precio oferta ganadora",
        ]

        for idx, header in enumerate(headers):
            worksheet.write(0, idx, header, header_format)

        row = 1
        for entry in scraped_data:
            print(entry)
            col = 0
            item = entry["item"]
            catalog = entry["catalog"]
            catalog_items = entry["catalog_items"]

            catalog_product_id = item["catalog_product_id"]
            if not catalog_product_id:
                continue

            seller_price = None
            if "results" not in catalog_items:
                # No winners found (?)
                continue
            for catalog_item in catalog_items["results"]:
                if str(catalog_item["seller_id"]) == seller_id:
                    seller_price = catalog_item["price"]

            winning_item = catalog_items["results"][0]

            if not seller_price:
                continue

            # ID Producto

            worksheet.write(row, col, str(catalog_product_id))
            col += 1

            # Nombre Producto

            worksheet.write(row, col, catalog["name"])
            col += 1

            # URL Producto

            worksheet.write(row, col, catalog["permalink"])
            col += 1

            # ID Dreamtec

            worksheet.write(row, col, item["id"])
            col += 1

            # Precio Dreamtec

            worksheet.write(row, col, seller_price)
            col += 1

            # ¿Oferta ganadora?

            is_winner = str(catalog["buy_box_winner"]["seller_id"]) == seller_id
            worksheet.write(row, col, is_winner)
            col += 1

            # Precio oferta ganadora

            worksheet.write(row, col, winning_item["price"])
            col += 1

            row += 1

        worksheet.autofilter(0, 0, row - 1, len(headers) - 1)

        workbook.close()

        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()

        filename_template = "mercadolibre_chile_catalog_%Y-%m-%d_%H:%M:%S"
        filename = timezone.now().strftime(filename_template)
        path = storage.save("reports/{}.xlsx".format(filename), file_for_upload)

        return {"file": file_value, "path": path}
