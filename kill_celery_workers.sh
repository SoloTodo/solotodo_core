#!/usr/bin/env sh
cat solotodo_core/pids/celery/*.pid | xargs kill -KILL