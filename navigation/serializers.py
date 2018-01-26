from rest_framework import serializers

from navigation.models import NavSection, NavItem


class NavItemSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = NavItem
        fields = ['name', 'path']


class NavSectionSerializer(serializers.HyperlinkedModelSerializer):
    items = NavItemSerializer(many=True)

    class Meta:
        model = NavSection
        fields = ['name', 'path', 'items']


class NavDepartmentSerializer(serializers.HyperlinkedModelSerializer):
    sections = NavSectionSerializer(many=True)

    class Meta:
        model = NavSection
        fields = ['name', 'sections']
