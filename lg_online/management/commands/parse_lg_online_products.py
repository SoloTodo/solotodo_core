import csv
import json

from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        d = []
        with open('lg_online/products.tsv') as f:
            reader = csv.reader(f, delimiter='\t')

            for idx, row in enumerate(reader):
                if idx == 0:
                    continue
                product, product_id, category, category_id, subcategory, \
                    frontpage_ordering_str, category_ordering_str, model, \
                    custom_title, custom_description, custom_1, custom_2, \
                    custom_3, main_picture_str, secondary_pictures_str, \
                    lg_url_str, flixmedia_mpn = row

                if not product_id:
                    print('Unavailable product ID: {}'.format(product))
                    continue

                if frontpage_ordering_str.strip():
                    frontpage_ordering = int(frontpage_ordering_str)
                else:
                    frontpage_ordering = None
                if category_ordering_str.strip():
                    category_ordering = int(category_ordering_str)
                else:
                    category_ordering = None
                if main_picture_str.strip():
                    main_picture_id = main_picture_str.split('id=')[1]
                else:
                    main_picture_id = None
                if secondary_pictures_str.strip():
                    secondary_pictures_id = secondary_pictures_str.split(
                        'id=')[1]
                else:
                    secondary_pictures_id = None
                if lg_url_str.strip():
                    lg_url = lg_url_str.strip()
                else:
                    lg_url = None
                d.append({
                    'productId': int(product_id),
                    'categoryId': int(category_id),
                    'customTitle': custom_title,
                    'customDescription': custom_description.strip(),
                    'frontpageOrdering': frontpage_ordering,
                    'categoryOrdering': category_ordering,
                    'custom_1': custom_1,
                    'custom_2': custom_2,
                    'custom_3': custom_3,
                    'mainPictureId': main_picture_id,
                    'secondaryPicturesId': secondary_pictures_id,
                    'lgUrl': lg_url,
                    'subcategory': subcategory,
                    'flixmediaMpn': flixmedia_mpn.strip() or None})

        with open('lg_online/products.json', 'w') as f:
            f.write(json.dumps(d, indent=4))
