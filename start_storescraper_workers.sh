#!/usr/bin/env zsh

# Starts the celery workers that actually scrap (make network requests) the stores
# If you run this on a macOS change the concurrency from 50 to somthing like 20, otherwise it doesn't work!
source ~/.zshrc

cd "${0%/*}"
source env/bin/activate
celery multi start -A solotodo_core storescraper -Q:storescraper storescraper -c:storescraper 25 --logfile=solotodo_core/logs/celery/%n.log --pidfile=solotodo_core/pids/celery/%n.pid -E -l info
