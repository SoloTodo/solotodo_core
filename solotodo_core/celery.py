import logging
import logstash
import os
from celery import Celery
from celery.signals import setup_logging


# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "solotodo_core.settings")

app = Celery("solotodo_core")

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@setup_logging.connect
def setup_celery_logging(**kwargs):
    logger = logging.getLogger("logstash")
    logger.setLevel(logging.INFO)
    logger.addHandler(logstash.TCPLogstashHandler("localhost", 5959))
