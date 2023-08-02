#!/usr/bin/env bash

if [[ "${CODESPACES}" != "true" ]]; then
  echo "This script can only be run within a GitHub codespace."
  exit 1
fi

if [[ ! -f "../notifications-api/create-codespace-user.sh" ]]; then
  echo -n "Enter an email address for your Notify user login: "
  read USER_EMAIL_ADDRESS
  echo -n "Enter a password for your Notify user login: "
  read USER_PASSWORD

  cat <<EOF | envsubst > ../notifications-api/create-codespace-user.py
from app.models import *
user = User(name='${USER_EMAIL_ADDRESS}', email_address='${USER_EMAIL_ADDRESS}', state='active', auth_type='email_auth', password='${USER_PASSWORD}', platform_admin=True)
db.session.add(user)
db.session.commit()
EOF
  chmod +x ../notifications-api/create-codespace-user.py
fi

source ${NVM_DIR}/nvm.sh

make generate-version-file
nvm install; nvm use; npm install; npm run build
(cd ../notifications-api; make generate-version-file)
(cd ../notifications-template-preview; make generate-version-file)
(cd ../notifications-antivirus; make generate-version-file)
(cd ../document-download-api; make generate-version-file)
(cd ../document-download-frontend; make generate-version-file; nvm install; nvm use; npm install; npm run build)

(cd ../notifications-local; ./generate-env-files.sh; docker-compose build; docker-compose run --entrypoint bash notify-api -c "cat create-codespace-user.py | flask shell"; make up)
