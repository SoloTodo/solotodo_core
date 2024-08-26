#!/usr/bin/env sh
env/bin/celery -A solotodo_core multi start store_update general reports storescraper -Q:store_update store_update -c:store_update 3 -Q:general general -c:general 10 -Q:reports reports -c:reports 4 -Q:storescraper storescraper -c:storescraper 20 --logfile=solotodo_core/logs/celery/%n.log --pidfile=solotodo_core/pids/celery/%n.pid -l info
