#!/usr/bin/env bash
celery multi stop -A solotodo_core store_update general --logfile=solotodo_core/logs/celery/%n.log --pidfile=solotodo_core/pids/celery/%n.pid -E -l info
