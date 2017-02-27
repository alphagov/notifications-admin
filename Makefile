.DEFAULT_GOAL := help
SHELL := /bin/bash
DATE = $(shell date +%Y-%m-%d:%H:%M:%S)

PIP_ACCEL_CACHE ?= ${CURDIR}/cache/pip-accel
APP_VERSION_FILE = app/version.py

GIT_BRANCH ?= $(shell git symbolic-ref --short HEAD 2> /dev/null || echo "detached")
GIT_COMMIT ?= $(shell git rev-parse HEAD 2> /dev/null || echo "")

DOCKER_IMAGE_TAG := $(shell cat docker/VERSION)
DOCKER_BUILDER_IMAGE_NAME = govuk/notify-admin-builder:${DOCKER_IMAGE_TAG}
DOCKER_TTY ?= $(if ${JENKINS_HOME},,t)

BUILD_TAG ?= notifications-admin-manual
BUILD_NUMBER ?= 0
DEPLOY_BUILD_NUMBER ?= ${BUILD_NUMBER}
BUILD_URL ?=

DOCKER_CONTAINER_PREFIX = ${USER}-${BUILD_TAG}

CODEDEPLOY_PREFIX ?= notifications-admin
CODEDEPLOY_APP_NAME ?= notify-admin

CF_API ?= api.cloud.service.gov.uk
CF_ORG ?= govuk-notify
CF_SPACE ?= ${DEPLOY_ENV}

.PHONY: help
help:
	@cat $(MAKEFILE_LIST) | grep -E '^[a-zA-Z_-]+:.*?## .*$$' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: venv
venv: venv/bin/activate ## Create virtualenv if it does not exist

venv/bin/activate:
	test -d venv || virtualenv venv -p python3
	. venv/bin/activate && pip install pip-accel

.PHONY: check-env-vars
check-env-vars: ## Check mandatory environment variables
	$(if ${DEPLOY_ENV},,$(error Must specify DEPLOY_ENV))
	$(if ${DNS_NAME},,$(error Must specify DNS_NAME))
	$(if ${AWS_ACCESS_KEY_ID},,$(error Must specify AWS_ACCESS_KEY_ID))
	$(if ${AWS_SECRET_ACCESS_KEY},,$(error Must specify AWS_SECRET_ACCESS_KEY))

.PHONY: sandbox
sandbox: ## Set environment to sandbox
	$(eval export DEPLOY_ENV=sandbox)
	$(eval export DNS_NAME="cloudapps.digital")
	@true

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

.PHONY: dependencies
dependencies: venv ## Install build dependencies
	npm set progress=false
	npm install
	npm rebuild node-sass
	mkdir -p ${PIP_ACCEL_CACHE}
	. venv/bin/activate && PIP_ACCEL_CACHE=${PIP_ACCEL_CACHE} pip-accel install -r requirements_for_test.txt

.PHONY: generate-version-file
generate-version-file: ## Generates the app version file
	@echo -e "__travis_commit__ = \"${GIT_COMMIT}\"\n__time__ = \"${DATE}\"\n__travis_job_number__ = \"${BUILD_NUMBER}\"\n__travis_job_url__ = \"${BUILD_URL}\"" > ${APP_VERSION_FILE}

.PHONY: build
build: dependencies generate-version-file ## Build project
	npm run build
	. venv/bin/activate && PIP_ACCEL_CACHE=${PIP_ACCEL_CACHE} pip-accel wheel --wheel-dir=wheelhouse -r requirements.txt

.PHONY: cf-build
cf-build: dependencies generate-version-file ## Build project
	npm run build

.PHONY: build-codedeploy-artifact
build-codedeploy-artifact: ## Build the deploy artifact for CodeDeploy
	rm -rf target
	mkdir -p target
	zip -y -q -r -x@deploy-exclude.lst target/notifications-admin.zip ./

.PHONY: upload-codedeploy-artifact ## Upload the deploy artifact for CodeDeploy
upload-codedeploy-artifact: check-env-vars
	$(if ${DEPLOY_BUILD_NUMBER},,$(error Must specify DEPLOY_BUILD_NUMBER))
	aws s3 cp --region eu-west-1 --sse AES256 target/notifications-admin.zip s3://${DNS_NAME}-codedeploy/${CODEDEPLOY_PREFIX}-${DEPLOY_BUILD_NUMBER}.zip

.PHONY: build-paas-artifact
build-paas-artifact: build-codedeploy-artifact ## Build the deploy artifact for PaaS

.PHONY: upload-paas-artifact ## Upload the deploy artifact for PaaS
upload-paas-artifact:
	$(if ${DEPLOY_BUILD_NUMBER},,$(error Must specify DEPLOY_BUILD_NUMBER))
	aws s3 cp --region eu-west-1 --sse AES256 target/notifications-admin.zip s3://notify.tools-jenkins/build/${CODEDEPLOY_PREFIX}/${DEPLOY_BUILD_NUMBER}.zip

.PHONY: test
test: venv ## Run tests
	./scripts/run_tests.sh

.PHONY: deploy
deploy: check-env-vars ## Upload deploy artifacts to S3 and trigger CodeDeploy
	aws deploy create-deployment --application-name ${CODEDEPLOY_APP_NAME} --deployment-config-name CodeDeployDefault.OneAtATime --deployment-group-name ${CODEDEPLOY_APP_NAME} --s3-location bucket=${DNS_NAME}-codedeploy,key=${CODEDEPLOY_PREFIX}-${DEPLOY_BUILD_NUMBER}.zip,bundleType=zip --region eu-west-1

.PHONY: check-aws-vars
check-aws-vars: ## Check if AWS access keys are set
	$(if ${AWS_ACCESS_KEY_ID},,$(error Must specify AWS_ACCESS_KEY_ID))
	$(if ${AWS_SECRET_ACCESS_KEY},,$(error Must specify AWS_SECRET_ACCESS_KEY))

.PHONY: deploy-suspend-autoscaling-processes
deploy-suspend-autoscaling-processes: check-aws-vars ## Suspend launch and terminate processes for the auto-scaling group
	aws autoscaling suspend-processes --region eu-west-1 --auto-scaling-group-name ${CODEDEPLOY_APP_NAME} --scaling-processes "Launch" "Terminate"

.PHONY: deploy-resume-autoscaling-processes
deploy-resume-autoscaling-processes: check-aws-vars ## Resume launch and terminate processes for the auto-scaling group
	aws autoscaling resume-processes --region eu-west-1 --auto-scaling-group-name ${CODEDEPLOY_APP_NAME} --scaling-processes "Launch" "Terminate"

.PHONY: deploy-check-autoscaling-processes
deploy-check-autoscaling-processes: check-aws-vars ## Returns with the number of instances with active autoscaling events
	@aws autoscaling describe-auto-scaling-groups --region eu-west-1 --auto-scaling-group-names ${CODEDEPLOY_APP_NAME} | jq '.AutoScalingGroups[0].Instances|map(select(.LifecycleState != "InService"))|length'

.PHONY: coverage
coverage: venv ## Create coverage report
	. venv/bin/activate && coveralls

.PHONY: prepare-docker-build-image
prepare-docker-build-image: ## Prepare the Docker builder image
	mkdir -p ${PIP_ACCEL_CACHE}
	make -C docker build

define run_docker_container
	@docker run -i${DOCKER_TTY} --rm \
		--name "${DOCKER_CONTAINER_PREFIX}-${1}" \
		-v "`pwd`:/var/project" \
		-v "${PIP_ACCEL_CACHE}:/var/project/cache/pip-accel" \
		-e UID=$(shell id -u) \
		-e GID=$(shell id -g) \
		-e GIT_COMMIT=${GIT_COMMIT} \
		-e BUILD_NUMBER=${BUILD_NUMBER} \
		-e BUILD_URL=${BUILD_URL} \
		-e http_proxy="${HTTP_PROXY}" \
		-e HTTP_PROXY="${HTTP_PROXY}" \
		-e https_proxy="${HTTPS_PROXY}" \
		-e HTTPS_PROXY="${HTTPS_PROXY}" \
		-e NO_PROXY="${NO_PROXY}" \
		-e COVERALLS_REPO_TOKEN=${COVERALLS_REPO_TOKEN} \
		-e CIRCLECI=1 \
		-e CI_NAME=${CI_NAME} \
		-e CI_BUILD_NUMBER=${BUILD_NUMBER} \
		-e CI_BUILD_URL=${BUILD_URL} \
		-e CI_BRANCH=${GIT_BRANCH} \
		-e CI_PULL_REQUEST=${CI_PULL_REQUEST} \
		-e CF_API="${CF_API}" \
		-e CF_USERNAME="${CF_USERNAME}" \
		-e CF_PASSWORD="${CF_PASSWORD}" \
		-e CF_ORG="${CF_ORG}" \
		-e CF_SPACE="${CF_SPACE}" \
		${DOCKER_BUILDER_IMAGE_NAME} \
		${2}
endef

.PHONY: build-with-docker
build-with-docker: prepare-docker-build-image ## Build inside a Docker container
	$(call run_docker_container,build,gosu hostuser make build)

.PHONY: cf-build-with-docker
cf-build-with-docker: prepare-docker-build-image ## Build inside a Docker container
	$(call run_docker_container,build,gosu hostuser make cf-build)

.PHONY: test-with-docker
test-with-docker: prepare-docker-build-image ## Run tests inside a Docker container
	$(call run_docker_container,test,gosu hostuser make test)

# FIXME: CIRCLECI=1 is an ugly hack because the coveralls-python library sends the PR link only this way
.PHONY: coverage-with-docker
coverage-with-docker: prepare-docker-build-image ## Generates coverage report inside a Docker container
	$(call run_docker_container,coverage,gosu hostuser make coverage)

.PHONY: clean-docker-containers
clean-docker-containers: ## Clean up any remaining docker containers
	docker rm -f $(shell docker ps -q -f "name=${DOCKER_CONTAINER_PREFIX}") 2> /dev/null || true

.PHONY: clean
clean:
	rm -rf node_modules cache target venv .coverage wheelhouse

.PHONY: cf-login
cf-login: ## Log in to Cloud Foundry
	$(if ${CF_USERNAME},,$(error Must specify CF_USERNAME))
	$(if ${CF_PASSWORD},,$(error Must specify CF_PASSWORD))
	$(if ${CF_SPACE},,$(error Must specify CF_SPACE))
	@echo "Logging in to Cloud Foundry on ${CF_API}"
	@cf login -a "${CF_API}" -u ${CF_USERNAME} -p "${CF_PASSWORD}" -o "${CF_ORG}" -s "${CF_SPACE}"

.PHONY: cf-deploy
cf-deploy: ## Deploys the app to Cloud Foundry
	$(if ${CF_SPACE},,$(error Must specify CF_SPACE))
	@cf app --guid notify-admin || exit 1
	cf rename notify-admin notify-admin-rollback
	cf push -f manifest-${CF_SPACE}.yml
	cf scale -i $$(cf curl /v2/apps/$$(cf app --guid notify-admin) | jq -r ".entity.instances" 2>/dev/null || echo "1") notify-admin
	cf stop notify-admin-rollback
	cf delete -f notify-admin-rollback

.PHONY: cf-rollback
cf-rollback: ## Rollbacks the app to the previous release
	@cf app --guid notify-admin-rollback || exit 1
	cf delete -f notify-admin || true
	cf rename notify-admin-rollback notify-admin

.PHONY: cf-push
cf-push:
	cf push -f manifest-${CF_SPACE}.yml

.PHONY: cf-deploy-with-docker
cf-deploy-with-docker: prepare-docker-build-image ## Deploys the app to Cloud Foundry from a new Docker container
	$(call run_docker_container,cf-deploy,make cf-login cf-deploy)

.PHONY: cf-rollback-with-docker
cf-rollback-with-docker: prepare-docker-build-image ## Rollbacks the app on Cloud Foundry to the previous version
	$(call run_docker_container,cf-rollback,make cf-login cf-rollback)
