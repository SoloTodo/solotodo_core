def additional_es_fields(elastic_search_result, model_name):
    if model_name != 'Groceries':
        return

    result = {}

    # Add a flat array with all the categories this product belongs to

    # Programatically find the keys belonging to the category field
    category_keys = set()
    for field_name in elastic_search_result.keys():
        if not field_name.startswith('category_'):
            continue

        base_field_name = \
            field_name.replace('category_', '').replace('parent_', '')

        category_keys.add(base_field_name)

    categories = []
    level = 0

    while True:
        if level > 10:
            raise Exception('Category overflow')

        level_id_field = 'category_{}id'.format('parent_' * level)
        if level_id_field not in elastic_search_result:
            break

        category = {}
        for category_key in category_keys:
            level_key_field = 'category_{}{}'.format('parent_' * level, category_key)
            category[category_key] = elastic_search_result[level_key_field]

        categories.append(category)

        level += 1

    # Reverse the list to make it from more general to more specific
    categories.reverse()

    result['categories'] = categories
    return result
