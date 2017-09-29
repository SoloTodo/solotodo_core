from django_filters import fields, filters


class IsoDateTimeRangeField(fields.RangeField):

    """Field for a datetime range in ISO-8601 format."""

    def __init__(self, *args, **kwargs):
        super().__init__((fields.IsoDateTimeField(),
                          fields.IsoDateTimeField()),
                         *args, **kwargs)


class IsoDateTimeFromToRangeFilter(filters.DateTimeFromToRangeFilter):

    """Filter for a datetime range in ISO-8601 format."""

    field_class = IsoDateTimeRangeField
