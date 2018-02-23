from django_filters import rest_framework

from carousel_slides.models import CarouselSlide


class CarouselSlideFilterSet(rest_framework.FilterSet):
    @property
    def qs(self):
        qs = super(CarouselSlideFilterSet, self).qs
        return qs.filter(ordering__isnull=False)

    class Meta:
        model = CarouselSlide
        fields = ('website',)
