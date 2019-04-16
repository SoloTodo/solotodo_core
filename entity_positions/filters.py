from django_filters import rest_framework

from .models import EntityPosition, EntityPositionSection


class EntityPositionFilterSet(rest_framework.FilterSet):
    @property
    def qs(self):
        qs = super(EntityPositionFilterSet, self).qs

        if self.request:
            qs = qs.filter_by_user_perms(self.request.user,
                                         'view_entity_positions')

        return qs

    class Meta:
        model = EntityPosition
        fields = []


class EntityPositionSectionFilterSet(rest_framework.FilterSet):
    @property
    def qs(self):
        qs = super(EntityPositionSectionFilterSet, self).qs

        if self.request:
            qs = qs.filter_by_user_perms(self.request.user,
                                         'view_entity_positions')

        return qs

    class Meta:
        model = EntityPositionSection
        fields = []
