import io
import xlsxwriter

from xlsxwriter.utility import xl_rowcol_to_cell
from django import forms
from django.db.models import Count, F
from django.core.files.base import ContentFile
from guardian.shortcuts import get_objects_for_user

from keyword_search_positions.models import KeywordSearchEntityPosition
from solotodo.models import Store, Category, Brand
from solotodo_core.s3utils import PrivateS3Boto3Storage


class KeywordSearchActivePositionsForm(forms.Form):
    store = forms.ModelChoiceField(
        queryset=Store.objects.all())

    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False)

    brands = forms.ModelMultipleChoiceField(
        queryset=Brand.objects.all(),
        required=False)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        valid_categories = get_objects_for_user(
            user, 'create_category_keyword_search', Category)
        self.fields['categories'].queryset = valid_categories

        valid_stores = get_objects_for_user(
            user, 'create_store_keyword_search', Store)
        self.fields['store'].queryset = valid_stores

    def clean_categories(self):
        selected_categories = self.cleaned_data['categories']
        if selected_categories:
            return selected_categories
        else:
            return self.fields['categories'].queryset

    def generate_report(self, user):
        store = self.cleaned_data['store']
        categories = self.cleaned_data['categories']
        brands = self.cleaned_data['brands']

        keyword_search_positions = KeywordSearchEntityPosition.objects.filter(
            update__search__active_update=F('update'),
            update__search__store=store,
            update__search__category__in=categories)

        if not user.is_superuser:
            # We assume the user only has one group
            group = user.groups.all()[0]

            keyword_search_positions = keyword_search_positions.filter(
                update__search__user__groups=group
            )

        category_keyword_raw_data = keyword_search_positions\
            .order_by(
                'update__search__category',
                'update__search__keyword')\
            .values(
                'update__search__category',
                'update__search__keyword')\
            .annotate(c=Count('*'))

        category_keyword_data = {
            (e['update__search__category'],
             e['update__search__keyword']): e['c']
            for e in category_keyword_raw_data}

        if brands:
            keyword_search_positions = keyword_search_positions.filter(
                entity__product__brand__in=brands)

        category_keyword_brand_raw_data = keyword_search_positions\
            .order_by(
                'update__search__category',
                'update__search__keyword',
                'entity__product__brand')\
            .values(
                'update__search__category',
                'update__search__keyword',
                'entity__product__brand')\
            .annotate(c=Count('*'))

        category_keyword_brand_data = {
            (e['update__search__category'],
             e['update__search__keyword'],
             e['entity__product__brand']): e['c']
            for e in category_keyword_brand_raw_data}

        # # # REPORT # # #
        output = io.BytesIO()

        workbook = xlsxwriter.Workbook(output)
        workbook.formats[0].set_font_size(10)

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter'
        })

        percentage_format = workbook.add_format()
        percentage_format.set_num_format('0.00%')
        percentage_format.set_font_size(10)

        percentage_bold_format = workbook.add_format()
        percentage_bold_format.set_num_format('0.00%')
        percentage_bold_format.set_font_size(10)
        percentage_bold_format.set_bold(True)

        bold_format = workbook.add_format()
        bold_format.set_font_size(10)
        bold_format.set_bold(True)

        for category in categories:
            keyword_search_positions_in_category = keyword_search_positions\
                .filter(update__search__category=category)

            keywords_in_category = [a['update__search__keyword'] for a in
                                    keyword_search_positions_in_category
                                    .order_by('update__search__keyword')
                                    .values('update__search__keyword')
                                    .distinct()]

            if brands:
                brands_in_category = brands
            else:
                brands_in_category = Brand.objects.filter(
                    pk__in=[e['entity__product__brand']
                            for e in keyword_search_positions_in_category
                            .order_by('entity__product__brand')
                            .values('entity__product__brand')])

            worksheet = workbook.add_worksheet()
            worksheet.name = category.name

            headers = ['Keyword']
            brand_headers = [str(brand) for brand in brands_in_category]

            for idx, header in enumerate(headers):
                worksheet.write(0, idx, header, header_format)

            for idx, header in enumerate(brand_headers):
                header_col = (idx * 2) + 1
                worksheet.merge_range(
                    0, header_col,
                    0, header_col + 1,
                    header,
                    header_format)

            total_col = len(brand_headers) * 2 + 1
            formula = '={}/{}'

            worksheet.write(0, total_col, 'Total', header_format)

            row = 1

            for keyword in keywords_in_category:
                col = 0
                worksheet.write(row, col, keyword)

                for brand in brands_in_category:
                    col += 1
                    worksheet.write(row, col, category_keyword_brand_data.get(
                        (category.id, keyword, brand.id), 0))

                    percentage_formula = formula.format(
                        xl_rowcol_to_cell(row, col),
                        xl_rowcol_to_cell(row, total_col))

                    col += 1
                    rowcol = xl_rowcol_to_cell(row, col)
                    worksheet.write_formula(rowcol, percentage_formula,
                                            percentage_format)

                col += 1
                worksheet.write(row, col, category_keyword_data.get(
                    (category.id, keyword), 0))

                row += 1

            col = 0
            worksheet.write(row, col, 'Total categoría', bold_format)

            for brand in brands_in_category:
                col += 1
                init_cell = xl_rowcol_to_cell(1, col)
                end_cell = xl_rowcol_to_cell(row-1, col)
                write_cell = xl_rowcol_to_cell(row, col)
                worksheet.write_formula(
                    write_cell, '=SUM({}:{})'.format(init_cell, end_cell),
                    bold_format)

                percentage_formula = formula.format(
                    write_cell,
                    xl_rowcol_to_cell(row, total_col)
                )

                col += 1
                rowcol = xl_rowcol_to_cell(row, col)
                worksheet.write_formula(rowcol, percentage_formula,
                                        percentage_bold_format)

            col += 1
            init_cell = xl_rowcol_to_cell(1, col)
            end_cell = xl_rowcol_to_cell(row - 1, col)
            write_cell = xl_rowcol_to_cell(row, col)
            worksheet.write_formula(
                write_cell, '=SUM({}:{})'.format(init_cell, end_cell),
                bold_format)

        workbook.close()
        output.seek(0)
        file_value = output.getvalue()
        file_for_upload = ContentFile(file_value)
        storage = PrivateS3Boto3Storage()
        filename = 'current_keyword_positions.xlsx'
        path = storage.save(filename, file_for_upload)

        return {
            'file': file_value,
            'path': path
        }
