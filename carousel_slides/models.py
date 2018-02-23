from django.db import models

from sorl.thumbnail import ImageField

from solotodo.models import Website


class CarouselSlide(models.Model):
    website = models.ForeignKey(Website, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    target_url = models.URLField()
    img_400 = ImageField(upload_to='carousel_slides')
    img_576 = ImageField(upload_to='carousel_slides')
    img_768 = ImageField(upload_to='carousel_slides')
    img_992 = ImageField(upload_to='carousel_slides')
    img_1200 = ImageField(upload_to='carousel_slides')
    ordering = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('ordering', )
