#!/usr/bin/env bash
cd "${0%/*}"
source env/bin/activate
celery multi start -A solotodo_core store_update general -Q:store_update store_update -c:store_update 5 -Q:general general -c:general 8 --logfile=solotodo_core/logs/celery/%n.log --pidfile=solotodo_core/pids/celery/%n.pid -E -l info