import io
from PIL import Image, ImageChops
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
    bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)


def convert_image_to_inmemoryfile(image):
    # Create a file-like object to write thumb data (thumb data previously
    # created using PIL, and stored in variable 'thumb')
    image_io = io.StringIO()
    image.save(image_io, format='png')

    # Create a new Django file-like object to be used in models as ImageField
    # using InMemoryUploadedFile.  If you look at the source in Django, a
    # SimpleUploadedFile is essentially instantiated similarly to what is
    # shown here
    inmemoryfile = InMemoryUploadedFile(
        image_io, None, 'foo.png', 'image/png', image_io.len, None)

    return inmemoryfile
