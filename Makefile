.DEFAULT_GOAL := help
SHELL := /bin/bash
DATE = $(shell date +%Y-%m-%dT%H:%M:%S)

APP_VERSION_FILE = app/version.py

GIT_BRANCH ?= $(shell git symbolic-ref --short HEAD 2> /dev/null || echo "detached")
GIT_COMMIT ?= $(shell git rev-parse HEAD 2> /dev/null || echo "")

CF_API ?= api.cloud.service.gov.uk
CF_ORG ?= govuk-notify
CF_SPACE ?= ${DEPLOY_ENV}
CF_HOME ?= ${HOME}
CF_APP ?= notify-admin
CF_MANIFEST_PATH ?= /tmp/manifest.yml
$(eval export CF_HOME)

NOTIFY_CREDENTIALS ?= ~/.notify-credentials

VIRTUALENV_ROOT := $(shell [ -z $$VIRTUAL_ENV ] && echo $$(pwd)/venv || echo $$VIRTUAL_ENV)


## DEVELOPMENT

.PHONY: bootstrap
bootstrap: generate-version-file ## Set up everything to run the app
	pip3 install -r requirements_for_test.txt
	npm install
	. environment.sh; npm run build

.PHONY: watch-frontend
watch-frontend:  ## Build frontend and watch for changes
	. environment.sh; npm run watch

.PHONY: run-flask
run-flask:  ## Run flask
	. environment.sh && flask run -p 6012

.PHONY: help
help:
	@cat $(MAKEFILE_LIST) | grep -E '^[a-zA-Z_-]+:.*?## .*$$' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: virtualenv
virtualenv:
	[ -z $$VIRTUAL_ENV ] && [ ! -d venv ] && python3 -m venv venv || true

.PHONY: upgrade-pip
upgrade-pip: virtualenv
	${VIRTUALENV_ROOT}/bin/pip install --upgrade pip

.PHONY: generate-version-file
generate-version-file: ## Generates the app version file
	@echo -e "__git_commit__ = \"${GIT_COMMIT}\"\n__time__ = \"${DATE}\"" > ${APP_VERSION_FILE}

.PHONY: test
test: ## Run tests
	flake8 .
	isort --check-only ./app ./tests
	npm test
	py.test -n auto --maxfail=10 tests/

.PHONY: fix-imports
fix-imports: ## Fix imports using isort
	isort ./app ./tests

.PHONY: freeze-requirements
freeze-requirements: ## create static requirements.txt
	${VIRTUALENV_ROOT}/bin/pip install --upgrade pip-tools
	${VIRTUALENV_ROOT}/bin/pip-compile requirements.in

.PHONY: clean
clean:
	rm -rf node_modules cache target ${CF_MANIFEST_PATH}


## DEPLOYMENT

.PHONY: check-env-vars
check-env-vars: ## Check mandatory environment variables
	$(if ${DEPLOY_ENV},,$(error Must specify DEPLOY_ENV))
	$(if ${DNS_NAME},,$(error Must specify DNS_NAME))

.PHONY: preview
preview: ## Set environment to preview
	$(eval export DEPLOY_ENV=preview)
	$(eval export DNS_NAME="notify.works")
	@true

.PHONY: staging
staging: ## Set environment to staging
	$(eval export DEPLOY_ENV=staging)
	$(eval export DNS_NAME="staging-notify.works")
	@true

.PHONY: production
production: ## Set environment to production
	$(eval export DEPLOY_ENV=production)
	$(eval export DNS_NAME="notifications.service.gov.uk")
	@true

.PHONY: cf-login
cf-login: ## Log in to Cloud Foundry
	$(if ${CF_USERNAME},,$(error Must specify CF_USERNAME))
	$(if ${CF_PASSWORD},,$(error Must specify CF_PASSWORD))
	$(if ${CF_SPACE},,$(error Must specify CF_SPACE))
	@echo "Logging in to Cloud Foundry on ${CF_API}"
	@cf login -a "${CF_API}" -u ${CF_USERNAME} -p "${CF_PASSWORD}" -o "${CF_ORG}" -s "${CF_SPACE}"

.PHONY: generate-manifest
generate-manifest:
	$(if ${CF_APP},,$(error Must specify CF_APP))
	$(if ${CF_SPACE},,$(error Must specify CF_SPACE))
	$(if $(shell which gpg2), $(eval export GPG=gpg2), $(eval export GPG=gpg))
	$(if ${GPG_PASSPHRASE_TXT}, $(eval export DECRYPT_CMD=echo -n $$$${GPG_PASSPHRASE_TXT} | ${GPG} --quiet --batch --passphrase-fd 0 --pinentry-mode loopback -d), $(eval export DECRYPT_CMD=${GPG} --quiet --batch -d))

	@jinja2 --strict manifest.yml.j2 \
	    -D environment=${CF_SPACE} \
	    -D CF_APP=${CF_APP} \
	    --format=yaml \
	    <(${DECRYPT_CMD} ${NOTIFY_CREDENTIALS}/credentials/${CF_SPACE}/paas/environment-variables.gpg) 2>&1

.PHONY: upload-static ## Upload the static files to be served from S3
upload-static:
	aws s3 cp --region eu-west-1 --recursive --cache-control max-age=315360000,immutable ./app/static s3://${DNS_NAME}-static

.PHONY: cf-deploy
cf-deploy: ## Deploys the app to Cloud Foundry
	$(if ${CF_SPACE},,$(error Must specify CF_SPACE))
	@cf app --guid notify-admin || exit 1
	# cancel any existing deploys to ensure we can apply manifest (if a deploy is in progress you'll see ScaleDisabledDuringDeployment)
	cf cancel-deployment ${CF_APP} || true

	# generate manifest (including secrets) and write it to CF_MANIFEST_PATH (in /tmp/)
	make -s CF_APP=${CF_APP} generate-manifest > ${CF_MANIFEST_PATH}
	# reads manifest from CF_MANIFEST_PATH
	CF_STARTUP_TIMEOUT=10 cf push ${CF_APP} --strategy=rolling -f ${CF_MANIFEST_PATH}
	# delete old manifest file
	rm -f ${CF_MANIFEST_PATH}

.PHONY: cf-deploy-prototype
cf-deploy-prototype: cf-target ## Deploys the first prototype to Cloud Foundry
	make -s CF_APP=notify-admin-prototype generate-manifest > ${CF_MANIFEST_PATH}
	cf push notify-admin-prototype --strategy=rolling -f ${CF_MANIFEST_PATH}
	rm -f ${CF_MANIFEST_PATH}

.PHONY: cf-deploy-prototype-2
cf-deploy-prototype-2: cf-target ## Deploys the second prototype to Cloud Foundry
	make -s CF_APP=notify-admin-prototype-2 generate-manifest > ${CF_MANIFEST_PATH}
	cf push notify-admin-prototype-2 --strategy=rolling -f ${CF_MANIFEST_PATH}
	rm -f ${CF_MANIFEST_PATH}

.PHONY: cf-rollback
cf-rollback: cf-target ## Rollbacks the app to the previous release
	cf cancel-deployment ${CF_APP}
	rm -f ${CF_MANIFEST_PATH}

.PHONY: cf-target
cf-target: check-env-vars
	@cf target -o ${CF_ORG} -s ${CF_SPACE}

.PHONY: cf-failwhale-deployed
cf-failwhale-deployed:
	@cf app notify-admin-failwhale --guid || (echo "notify-admin-failwhale is not deployed on ${CF_SPACE}" && exit 1)

.PHONY: enable-failwhale
enable-failwhale: cf-target cf-failwhale-deployed ## Enable the failwhale app and disable admin
	@cf map-route notify-admin-failwhale ${DNS_NAME} --hostname www
	@cf unmap-route notify-admin ${DNS_NAME} --hostname www
	@echo "Failwhale is enabled"

.PHONY: disable-failwhale
disable-failwhale: cf-target cf-failwhale-deployed ## Disable the failwhale app and enable admin
	@cf map-route notify-admin ${DNS_NAME} --hostname www
	@cf unmap-route notify-admin-failwhale ${DNS_NAME} --hostname www
	@echo "Failwhale is disabled"
