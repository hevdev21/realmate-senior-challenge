#!/bin/sh
set -e

export PYTHONPATH="${PYTHONPATH}:${PWD}/src"

exec celery -A config beat -l INFO
