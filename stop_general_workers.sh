#!/usr/bin/env bash
celery multi stop -A solotodo_try store_update --logfile=solotodo_try/logs/celery/%n.log --pidfile=solotodo_try/pids/celery/%n.pid -E -l info