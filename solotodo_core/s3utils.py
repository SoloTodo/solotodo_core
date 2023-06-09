from storages.utils import setting
from storages.backends.s3boto3 import S3Boto3Storage


class StaticRootS3Boto3Storage(S3Boto3Storage):
    location = setting('AWS_LOCATION', 'static')
    querystring_auth = False


class MediaRootS3Boto3Storage(S3Boto3Storage):
    location = setting('AWS_LOCATION', 'media')
    file_overwrite = False
    querystring_auth = False
    default_acl = 'public-read'


class MediaRootPrivateS3Boto3Storage(S3Boto3Storage):
    location = setting('AWS_LOCATION', 'media')
    file_overwrite = False
    querystring_auth = True


def PrivateS3Boto3Storage():
    return S3Boto3Storage(
        default_acl='private',
        custom_domain=None
    )


def PrivateSaS3Boto3Storage():
    from django.conf import settings

    return S3Boto3Storage(
        default_acl='private',
        bucket_name=settings.AWS_SA_STORAGE_BUCKET_NAME
    )
