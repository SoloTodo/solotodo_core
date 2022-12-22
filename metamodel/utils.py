import io
from PIL import Image, ImageChops
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile


def strip_whitespace(text):
    return ' '.join([e for e in text.split() if e])


def trim(im):
    """
    Autocrops the given image (a.k.a. removes the white borders)
    REF: http://stackoverflow.com/questions/10615901/trim-whitespace-using-pil
    :param im:
    :return:
    """
    rgb_im = im.convert('RGB')
    bg = Image.new(rgb_im.mode, rgb_im.size, rgb_im.getpixel((0, 0)))
    diff = ImageChops.difference(rgb_im, bg)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)


def convert_image_to_inmemoryfile(image):
    new_image_io = io.BytesIO()
    image.save(new_image_io, format='png')
    inmemoryfile = ContentFile(new_image_io.getvalue())

    return inmemoryfile
