#!/bin/sh
set -eu
host_uid="${HOST_UID:-1000}"
host_gid="${HOST_GID:-1000}"
case "$host_uid" in *[!0-9]*) echo "HOST_UID must be numeric" >&2; exit 2 ;; esac
if ! [ "$host_uid" -gt 0 ]; then
    echo "HOST_UID must be greater than zero" >&2
    exit 2
fi
case "$host_gid" in *[!0-9]*) echo "HOST_GID must be numeric" >&2; exit 2 ;; esac

# Apache resolves its numeric worker UID through NSS before dropping privileges.
if ! getent group "$host_gid" >/dev/null; then
    groupadd --gid "$host_gid" "wsc-local-gid-$host_gid"
fi
if ! getent passwd "$host_uid" >/dev/null; then
    useradd --uid "$host_uid" --gid "$host_gid" --no-user-group --no-create-home \
        --no-log-init --shell /usr/sbin/nologin "wsc-local-uid-$host_uid"
fi
export APACHE_RUN_USER="#${host_uid}"
export APACHE_RUN_GROUP="#${host_gid}"
exec apache2-foreground
