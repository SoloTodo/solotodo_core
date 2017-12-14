#!/usr/bin/env bash
celery multi stop -A solotodo_core storescraper --logfile=solotodo_core/logs/celery/%n.log --pidfile=solotodo_core/pids/celery/%n.pid -E -l info