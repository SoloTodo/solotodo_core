"""
Django settings for solotodo_try project.

Generated by 'django-admin startproject' using Django 1.11.3.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""
import logging
import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from django_filters import STRICTNESS
from elasticsearch import Elasticsearch


def _(s):
    return s

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'guardian',
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'crispy_forms',
    'storages',
    'sorl.thumbnail',
    'custom_user',
    'corsheaders',
    'django_premailer',
    'gtin_fields',
    'polymorphic',
    'metamodel',
    'solotodo',
    'category_templates',
    'reports',
    'mailing',
    'category_specs_forms',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'querycount.middleware.QueryCountMiddleware',
]

ROOT_URLCONF = 'solotodo_try.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'solotodo_try.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'solotodo_try',
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.'
                'UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.'
                'MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.'
                'CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.'
                'NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

LANGUAGES = [
    ('en', _('English')),
    ('es', _('Spanish')),
]

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'


#############################################################################
# Customized settings
#############################################################################

AUTH_USER_MODEL = 'solotodo.SoloTodoUser'

DEFAULT_FILE_STORAGE = 'solotodo_try.s3utils.MediaRootS3Boto3Storage'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)

GEOIP_PATH = BASE_DIR

#############################################################################
# Celery configurations
#############################################################################

CELERY_ENABLE_UTC = True

CELERY_BROKER_URL = 'amqp://solotodo_try:solotodo_try@localhost/solotodo_try'
CELERY_RESULT_BACKEND = 'rpc://'

CELERY_IMPORTS = (
    'storescraper.store'
)

CELERYD_TASK_TIME_LIMIT = 300

##############################################################################
# Django storages configuration
##############################################################################

AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''
AWS_STORAGE_BUCKET_NAME = 'solotodo-try'
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_REGION_NAME = 'us-east-2'

##############################################################################
# DRF Configuration
##############################################################################

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    )
}

##############################################################################
# CORS headers configuration
##############################################################################

CORS_ORIGIN_WHITELIST = ['localhost:3000', ]

###############################################################################
# Django-guardian Configuration
###############################################################################

ANONYMOUS_USER_NAME = 'anonymous@solotodo.com'

###############################################################################
# Django QueryCount configuration
###############################################################################

QUERYCOUNT = {
    'THRESHOLDS': {
        'MEDIUM': 50,
        'HIGH': 200,
        'MIN_TIME_TO_LOG': 0,
        'MIN_QUERY_COUNT_TO_LOG': 0
    },
    'IGNORE_REQUEST_PATTERNS': [],
    'IGNORE_SQL_PATTERNS': [],
    'DISPLAY_DUPLICATES': None
}

###############################################################################
# Django crispy forms configuration
###############################################################################

CRISPY_TEMPLATE_PACK = 'bootstrap3'

###############################################################################
# Django filter configuration
###############################################################################

FILTERS_STRICTNESS = STRICTNESS.RAISE_VALIDATION_ERROR

##############################################################################
# Premailer configuration
##############################################################################

PREMAILER_OPTIONS = {
    'strip_important': False,
    'cssutils_logging_level': logging.ERROR
}

##############################################################################
# Django-codemirror
##############################################################################

CODEMIRROR_PATH = 'node_modules/codemirror'

##############################################################################
# PubNub configuration
##############################################################################

BACKEND_CHANNEL = 'backend'
PUBNUB = None

##############################################################################
# Made up settings
##############################################################################

DEFAULT_CURRENCY = 4
DEFAULT_COUNTRY = 1
BOT_USERNAME = 'solobot@solotodo.com'
BACKEND_HOST = 'http://192.168.90.111:3000/'
CELL_PLAN_CATEGORY = 20

METAMODEL = {
    'DEBUG': False,
    'ADDITIONAL_ELASTICSEARCH_FIELDS_FUNCTIONS': [
        'solotodo.metamodel_custom_functions.brand_unicode.brand_unicode',
        'solotodo.metamodel_custom_functions.notebooks.additional_es_fields',
        'solotodo.metamodel_custom_functions.hardware.additional_es_fields',
        'solotodo.metamodel_custom_functions.electro.additional_es_fields',
        'solotodo.metamodel_custom_functions.smartphones.additional_es_fields'
    ],
    'MEDIA_PATH': 'products',
    'UNICODE_FUNCTIONS': [
        'solotodo.metamodel_custom_functions.hardware.unicode_function',
        'solotodo.metamodel_custom_functions.electro.unicode_function',
        'solotodo.metamodel_custom_functions.smartphones.unicode_function',
    ],
    'ORDERING_FUNCTIONS': [
        'solotodo.metamodel_custom_functions.notebooks.ordering_value'
    ]
}

ES = Elasticsearch([{"host": "localhost", "port": 9201}])
ES_PRODUCTS_INDEX = 'products'
