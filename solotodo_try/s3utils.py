from storages.backends.s3boto3 import S3Boto3Storage


def StaticRootS3Boto3Storage():
    return S3Boto3Storage(location='static', querystring_auth=False)


def MediaRootS3Boto3Storage():
    return S3Boto3Storage(location='media', querystring_auth=True)


def PrivateS3Boto3Storage():
    return S3Boto3Storage(default_acl='private')
