def pretty_dimensions(elastic_dict, axes=None, unit='mm'):
    """
    Returns a prettified version of the dimensions of the product or a
    default message if no info is available
    """
    if not axes:
        axes = ['width', 'height', 'depth']

    if elastic_dict.get(axes[0]) and elastic_dict.get(axes[1]) and \
            elastic_dict.get(axes[2]):
        result = '{} x {} x {}'.format(*[elastic_dict[axis] for axis in axes])
        result += ' ' + unit
        return result
    else:
        return 'N/A'


def format_optional_field(field, format_field='', value_if_false='N/A'):
    if field:
        return '{} {}'.format(field, format_field).strip()
    else:
        return value_if_false
