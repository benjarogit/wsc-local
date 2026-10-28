#!/bin/sh
set -eu
host_uid="${HOST_UID:-1000}"
host_gid="${HOST_GID:-1000}"
case "$host_uid" in ''|*[!0-9]*) echo "HOST_UID must be numeric" >&2; exit 2 ;; esac
case "$host_gid" in ''|*[!0-9]*) echo "HOST_GID must be numeric" >&2; exit 2 ;; esac
sed -i "s/^user = .*/user = ${host_uid}/; s/^group = .*/group = ${host_gid}/" /usr/local/etc/php-fpm.d/www.conf
exec php-fpm -F
