from storages.backends.s3boto3 import S3Boto3Storage


def StaticRootS3BotoStorage():
    return S3Boto3Storage(location='static', querystring_auth=False)


def MediaRootS3BotoStorage():
    return S3Boto3Storage(location='media', querystring_auth=True)


def PrivateS3BotoStorage():
    return S3Boto3Storage(default_acl='private')
