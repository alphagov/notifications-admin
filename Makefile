.DEFAULT_GOAL := help
SHELL := /bin/bash
DATE = $(shell date +%Y-%m-%d:%H:%M:%S)

PIP_ACCEL_CACHE ?= ${CURDIR}/cache/pip-accel
APP_VERSION_FILE = app/version.py

GIT_BRANCH = $(shell git symbolic-ref --short HEAD 2> /dev/null || echo "detached")
GIT_COMMIT ?= $(shell git rev-parse HEAD)

DOCKER_BUILDER_IMAGE_NAME = govuk/notify-admin-builder

BUILD_TAG ?= notifications-admin-manual
BUILD_NUMBER ?= 0
BUILD_URL ?=

DOCKER_CONTAINER_PREFIX = ${USER}-${BUILD_TAG}

.PHONY: help
help:
	@cat $(MAKEFILE_LIST) | grep -E '^[a-zA-Z_-]+:.*?## .*$$' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: venv
venv: venv/bin/activate ## Create virtualenv if it does not exist

venv/bin/activate:
	test -d venv || virtualenv venv
	./venv/bin/pip install pip-accel

.PHONY: check-env-vars
check-env-vars: ## Check mandatory environment variables
	$(if ${DEPLOY_ENV},,$(error Must specify DEPLOY_ENV))
	$(if ${DNS_NAME},,$(error Must specify DNS_NAME))
	$(if ${AWS_ACCESS_KEY_ID},,$(error Must specify AWS_ACCESS_KEY_ID))
	$(if ${AWS_SECRET_ACCESS_KEY},,$(error Must specify AWS_SECRET_ACCESS_KEY))

.PHONY: development
development: ## Set environment to development
	$(eval export DEPLOY_ENV=development)
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

.PHONY: dependencies
dependencies: venv ## Install build dependencies
	npm set progress=false
	npm install
	npm rebuild node-sass
	mkdir -p ${PIP_ACCEL_CACHE}
	PIP_ACCEL_CACHE=${PIP_ACCEL_CACHE} ./venv/bin/pip-accel install -r requirements_for_test.txt

.PHONY: generate-version-file
generate-version-file: ## Generates the app version file
	@echo -e "__travis_commit__ = \"${GIT_COMMIT}\"\n__time__ = \"${DATE}\"\n__travis_job_number__ = \"${BUILD_NUMBER}\"\n__travis_job_url__ = \"${BUILD_URL}\"" > ${APP_VERSION_FILE}

.PHONY: build
build: dependencies generate-version-file ## Build project
	npm run build

.PHONY: build-codedeploy-artifact
build-codedeploy-artifact: check-env-vars ## Build the deploy artifact for CodeDeploy
	mkdir -p target
	zip -r -x@deploy-exclude.lst target/notify-admin.zip *
	aws s3 cp --region eu-west-1 target/notify-admin.zip s3://${DNS_NAME}-codedeploy/notify-admin-${BUILD_NUMBER}-${GIT_COMMIT}.zip

.PHONY: test
test: venv ## Run tests
	./scripts/run_tests.sh

.PHONY: deploy
deploy: check-env-vars ## Upload deploy artifacts to S3 and trigger CodeDeploy
	aws deploy create-deployment --application-name notify-admin --deployment-config-name CodeDeployDefault.OneAtATime --deployment-group-name notify-admin --s3-location bucket=${DNS_NAME}-codedeploy,key=notify-admin-${BUILD_NUMBER}-${GIT_COMMIT}.zip,bundleType=zip --region eu-west-1

.PHONY: coverage
coverage: venv ## Create coverage report
	./venv/bin/coveralls

.PHONY: prepare-docker-build-image
prepare-docker-build-image: ## Prepare the Docker builder image
	mkdir -p ${PIP_ACCEL_CACHE}
	make -C docker build-build-image

.PHONY: build-with-docker
build-with-docker: prepare-docker-build-image ## Build inside a Docker container
	docker run -i --rm \
		--name "${DOCKER_CONTAINER_PREFIX}-build" \
		-v `pwd`:/var/project \
		-v ${PIP_ACCEL_CACHE}:/var/project/cache/pip-accel \
		${DOCKER_BUILDER_IMAGE_NAME} \
		make build

.PHONY: test-with-docker
test-with-docker: prepare-docker-build-image ## Run tests inside a Docker container
	docker run -i --rm \
		--name "${DOCKER_CONTAINER_PREFIX}-test" \
		-v `pwd`:/var/project \
		${DOCKER_BUILDER_IMAGE_NAME} \
		make test

.PHONY: coverage
coverage-with-docker: prepare-docker-build-image ## Generates coverage report inside a Docker container
	docker run -i --rm \
		--name "${DOCKER_CONTAINER_PREFIX}-coverage" \
		-v `pwd`:/var/project \
		${DOCKER_BUILDER_IMAGE_NAME} \
		make coverage

.PHONY: build-codedeploy-artifact-with-docker
build-codedeploy-artifact-with-docker: prepare-docker-build-image ## Run build-codedeploy-artifact inside a Docker container
	docker run -i --rm \
		--name "${DOCKER_CONTAINER_PREFIX}-deploy" \
		-v `pwd`:/var/project \
		-e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
		-e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
		-e DEPLOY_ENV=${DEPLOY_ENV} \
		-e DNS_NAME=${DNS_NAME} \
		${DOCKER_BUILDER_IMAGE_NAME} \
		make build-codedeploy-artifact

.PHONY: deploy-with-docker
deploy-with-docker: prepare-docker-build-image ## Run deploy inside a Docker container
	docker run -i --rm \
		--name "${DOCKER_CONTAINER_PREFIX}-deploy" \
		-v `pwd`:/var/project \
		-e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
		-e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
		-e DEPLOY_ENV=${DEPLOY_ENV} \
		-e DNS_NAME=${DNS_NAME} \
		${DOCKER_BUILDER_IMAGE_NAME} \
		make deploy

.PHONY: clean-docker-containers
clean-docker-containers: ## Clean up any remaining docker containers
	docker rm -f $(shell docker ps -q -f "name=${DOCKER_CONTAINER_PREFIX}") 2> /dev/null || true

clean:
	rm -rf node_modules cache target venv .coverage
