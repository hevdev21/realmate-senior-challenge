#!/bin/sh
set -e

export PYTHONPATH="${PYTHONPATH}:${PWD}/src"

CELERY_CMD="celery -A config worker -l INFO"

if [ "$ENVIRONMENT" = "local" ]; then
    watchmedo auto-restart \
        --directory=./src \
        --pattern=*.py \
        --recursive \
        --signal SIGTERM \
        --kill-after 10 \
        --interval 0.5 \
        -- $CELERY_CMD
else
    exec $CELERY_CMD
fi
