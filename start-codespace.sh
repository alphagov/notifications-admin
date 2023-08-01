#!/usr/bin/env bash

if [[ "${CODESPACES}" != "true" ]]; then
  echo "This script can only be run within a GitHub codespace."
  exit 1
fi

source ${NVM_DIR}/nvm.sh

make generate-version-file
nvm install; nvm use; npm install; npm run build
(cd ../notifications-api; make generate-version-file)
(cd ../notifications-template-preview; make generate-version-file)
(cd ../notifications-antivirus; make generate-version-file)
(cd ../document-download-api; make generate-version-file)
(cd ../document-download-frontend; make generate-version-file; nvm install; nvm use; npm install; npm run build)

(cd ../notifications-local; ./generate-env-files.sh; docker-compose build; make up)
