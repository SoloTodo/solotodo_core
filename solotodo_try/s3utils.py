from storages.utils import setting
from storages.backends.s3boto3 import S3Boto3Storage


class StaticRootS3Boto3Storage(S3Boto3Storage):
    location = setting('AWS_LOCATION', 'static')
    querystring_auth = False


class MediaRootS3Boto3Storage(S3Boto3Storage):
    location = setting('AWS_LOCATION', 'media')


def PrivateS3Boto3Storage():
    return S3Boto3Storage(default_acl='private')
