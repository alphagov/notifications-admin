#!/usr/bin/env bash

if [[ "${CODESPACES}" != "true" ]]; then
  echo "This script can only be run within a GitHub codespace."
  exit 1
fi

if [[ ! -f "../notifications-api/create-codespace-user.sh" ]]; then
  echo -n "Enter your email address for your Notify user login: "
  read USER_EMAIL_ADDRESS
  echo -n "Enter a password for your Notify user login: "
  read USER_PASSWORD
  echo -n "Enter your mobile number (07 format, no spaces, no typos, be careful): "
  read USER_MOBILE_NUMBER

  cat <<EOF | envsubst > ../notifications-api/create-codespace-user.py
from app.models import *
user = User(name='${USER_EMAIL_ADDRESS}', email_address='${USER_EMAIL_ADDRESS}', mobile_number='${USER_MOBILE_NUMBER}', state='active', auth_type='email_auth', password='${USER_PASSWORD}', platform_admin=True)
db.session.add(user)
db.session.commit()
EOF
  chmod +x ../notifications-api/create-codespace-user.py
fi

source ${NVM_DIR}/nvm.sh

make generate-version-file
nvm install; nvm use; npm install; npm run build
(cd ../notifications-api; git checkout main; git pull; make generate-version-file)
(cd ../notifications-template-preview; git checkout main; git pull; make generate-version-file)
(cd ../notifications-antivirus; git checkout main; git pull; make generate-version-file)
(cd ../document-download-api; git checkout main; git pull; make generate-version-file)
(cd ../document-download-frontend; git checkout main; git pull; make generate-version-file; nvm install; nvm use; npm install; npm run build)

(cd ../notifications-local; git checkout SW-codespace-support; git pull; ./generate-env-files.sh; docker-compose build; docker-compose run notify-api-db-migration; docker-compose run --entrypoint bash notify-api -c "cat create-codespace-user.py | flask shell"; make up)
