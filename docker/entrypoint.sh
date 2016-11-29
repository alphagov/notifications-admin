#!/usr/bin/env bash

set -eo pipefail

if [ -z "$UID" ] || [ "$UID" = "0" ]; then
  echo "UID must be specified as a positive integer"
  exit 1
fi

if [ -z "$GID" ] || [ "$GID" = "0" ]; then
  echo "GID must be specified as positive integer"
  exit 1
fi

USER=$(id -un $UID 2>/dev/null || echo "hostuser")
GROUP=$(getent group $GID | cut -d: -f1 || echo "hostgroup")

if [ "$USER" = "hostuser" ]; then
  useradd -u $UID -s /bin/bash -m $USER
fi

if [ "$GROUP" = "hostgroup" ]; then
  groupadd -g $GID $GROUP
fi

usermod -g $GROUP $USER

exec "$@"
