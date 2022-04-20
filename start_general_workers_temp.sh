#!/usr/bin/env zsh
source ~/.zshrc

cd "${0%/*}"
source env/bin/activate
celery multi start -A solotodo_core general -Q:general general -c:general 50 --logfile=solotodo_core/logs/celery/%n.log --pidfile=solotodo_core/pids/celery/%n.pid -E -l info
