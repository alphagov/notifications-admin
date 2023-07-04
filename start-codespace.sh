#!/usr/bin/env bash

if [[ "${CODESPACES}" != "true" ]]; then
  echo "This script can only be run within a GitHub codespace."
  exit 1
fi

(cd ../notifications-local; make up)
