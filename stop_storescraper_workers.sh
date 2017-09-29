#!/usr/bin/env bash
celery multi stop -A solotodo_try storescraper --logfile=solotodo_try/logs/celery/%n.log --pidfile=solotodo_try/pids/celery/%n.pid -E -l info