SOLOTODO_COM_SITE = None


def solotodo_com_site():
    from django.contrib.sites.models import Site
    from django.conf import settings

    global SOLOTODO_COM_SITE

    if not SOLOTODO_COM_SITE:
        SOLOTODO_COM_SITE = Site.objects.get(pk=settings.SOLOTODO_COM_SITE_ID)

    return SOLOTODO_COM_SITE
