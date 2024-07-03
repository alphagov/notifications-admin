.DEFAULT_GOAL := help
SHELL := /bin/bash
DATE = $(shell date +%Y-%m-%dT%H:%M:%S)

APP_VERSION_FILE = app/version.py

GIT_BRANCH ?= $(shell git symbolic-ref --short HEAD 2> /dev/null || echo "detached")
GIT_COMMIT ?= $(shell git rev-parse HEAD 2> /dev/null || echo "")

NOTIFY_CREDENTIALS ?= ~/.notify-credentials

VIRTUALENV_ROOT := $(shell [ -z $$VIRTUAL_ENV ] && echo $$(pwd)/venv || echo $$VIRTUAL_ENV)
PYTHON_EXECUTABLE_PREFIX := $(shell test -d "$${VIRTUALENV_ROOT}" && echo "$${VIRTUALENV_ROOT}/bin/" || echo "")

## DEVELOPMENT

.PHONY: bootstrap
bootstrap: generate-version-file ## Set up everything to run the app
	python -c "from notifications_utils.version_tools import copy_config; copy_config()"

	${PYTHON_EXECUTABLE_PREFIX}pip3 install -r requirements_for_test.txt

	source $(HOME)/.nvm/nvm.sh && nvm install && npm ci --no-audit
	. environment.sh; source $(HOME)/.nvm/nvm.sh && npm run build

.PHONY: bootstrap-with-docker
bootstrap-with-docker: generate-version-file ## Build the image to run the app in Docker
	docker build -f docker/Dockerfile --target test -t notifications-admin .

.PHONY: watch-frontend
watch-frontend:  ## Build frontend and watch for changes
	. environment.sh; npm run watch

.PHONY: run-flask
run-flask:  ## Run flask
	. environment.sh && flask run -p 6012

.PHONY: run-flask-with-docker
run-flask-with-docker: ## Run flask
	./scripts/run_with_docker.sh web-local

.PHONY: npm-audit
npm-audit:  ## Check for vulnerabilities in NPM packages
	source $(HOME)/.nvm/nvm.sh && npm run audit

.PHONY: help
help:
	@cat $(MAKEFILE_LIST) | grep -E '^[a-zA-Z_-]+:.*?## .*$$' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: virtualenv
virtualenv:
	[ -z $$VIRTUAL_ENV ] && [ ! -d venv ] && python3 -m venv venv || true

.PHONY: upgrade-pip
upgrade-pip: virtualenv
	${PYTHON_EXECUTABLE_PREFIX}pip3 install --upgrade pip

.PHONY: generate-version-file
generate-version-file: ## Generates the app version file
	@echo -e "__git_commit__ = \"${GIT_COMMIT}\"\n__time__ = \"${DATE}\"" > ${APP_VERSION_FILE}

.PHONY: test
test: ## Run tests
	ruff check .
	black --check .
	source $(HOME)/.nvm/nvm.sh && npm test
	py.test -n auto --maxfail=10 tests/

.PHONY: watch-tests
watch-tests: ## Watch tests and run on change
	ptw --runner "pytest --testmon -n auto"

.PHONY: test-with-docker
test-with-docker: ## Run tests in Docker container
	./scripts/run_with_docker.sh make test

.PHONY: fix-imports
fix-imports: ## Fix imports using ruff
	ruff --fix --select=I .

.PHONY: freeze-requirements
freeze-requirements: ## create static requirements.txt
	${PYTHON_EXECUTABLE_PREFIX}pip3 install --upgrade pip-tools
	${PYTHON_EXECUTABLE_PREFIX}pip-compile requirements.in
	${PYTHON_EXECUTABLE_PREFIX}pip-compile requirements_for_test.in

.PHONY: bump-utils
bump-utils:  # Bump notifications-utils package to latest version
	${PYTHON_EXECUTABLE_PREFIX}python -c "from notifications_utils.version_tools import upgrade_version; upgrade_version()"

.PHONY: clean
clean:
	rm -rf node_modules cache target

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

.PHONY: upload-static ## Upload the static files to be served from S3
upload-static: check-env-vars
	aws s3 cp --region eu-west-1 --recursive --cache-control max-age=315360000,immutable ./app/static s3://${DNS_NAME}-static
