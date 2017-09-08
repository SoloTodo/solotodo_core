def brand_unicode(instance_model, elastic_search_original):
    if 'brand_unicode' in elastic_search_original:
        return {}

    # Try common combinations (line.brand, line.brand.family)

    patterns = [
        'line_brand_unicode',
        'line_family_brand_unicode',
    ]

    for pattern in patterns:
        try:
            return {
                'brand_unicode': elastic_search_original[pattern]
            }
        except KeyError:
            pass
