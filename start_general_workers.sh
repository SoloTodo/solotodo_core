#!/usr/bin/env zsh
source ~/.zshrc

cd "${0%/*}"
source env/bin/activate
celery multi start -A solotodo_core store_update general reports -Q:store_update store_update -c:store_update 5 -Q:general general -c:general 12 -Q:reports reports -c:reports 5 --logfile=solotodo_core/logs/celery/%n.log --pidfile=solotodo_core/pids/celery/%n.pid -E -l info
