#!/usr/bin/env bash
set -euo pipefail

main() {
    config
}

config() {
    # Ignore if sysctl failed because this maybe don't work inside container
    set +e

    sysctl -w net.core.netdev_max_backlog=4096
    sysctl -w net.core.somaxconn=4096
    set -e

    # Start application depend on ROLE
    if [ "${ROLE}" = 'worker' ] ; then
        exec celery -A root worker -l info
    elif [ "${ROLE}" = 'worker-custom' ] ; then
        exec celery -A root worker -Q "$WORKER_QUEUE" -l info
    elif [ "${ROLE}" = 'beat' ] ; then
        exec celery -A root beat -l info
    elif [ "${ROLE}" = 'beat-django' ] ; then
        exec celery -A root beat -l info -S django
    elif [ "${ROLE}" = 'monitor' ] ; then
        exec celery -A root flower
    else
        exec uwsgi --spooler-quiet --ini /app/.deploy/uwsgi/uwsgi.ini --listen `cat /proc/sys/net/core/somaxconn`
    fi
}

main "$@"
