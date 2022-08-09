from django.db import models
from sorl.thumbnail import ImageField


class WebsiteSlideAsset(models.Model):
    picture = ImageField(upload_to='website_slides')
    theme_color = models.CharField(max_length=6)


class WebsiteSlide(models.Model):
    asset = models.ForeignKey(WebsiteSlideAsset, on_delete=models.CASCADE)
    destination_url = models.URLField()
    categories = models.ManyToManyField('solotodo.Category')
    category_priority = models.IntegerField(null=True, blank=True)
    home_priority = models.IntegerField(null=True, blank=True)



