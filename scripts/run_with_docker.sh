#!/bin/bash
DOCKER_IMAGE_NAME=notifications-admin

source environment.sh

REDIS_URL=${REDIS_URL:-"redis://host.docker.internal:6379"}
ADMIN_BASE_URL=${ADMIN_BASE_URL:-"http://host.docker.internal:6012"}
API_HOST_NAME=${API_HOST_NAME:-"http://host.docker.internal:6011"}
TEMPLATE_PREVIEW_API_HOST=${TEMPLATE_PREVIEW_API_HOST:-"http://host.docker.internal:6013"}
ANTIVIRUS_API_HOST=${ANTIVIRUS_API_HOST:-"http://host.docker.internal:6016"}

docker run -it --rm \
  -e NOTIFY_ENVIRONMENT=development \
  -e FLASK_DEBUG=${FLASK_DEBUG:-1} \
  -e WERKZEUG_DEBUG_PIN=${WERKZEUG_DEBUG_PIN:-"off"} \
  -e FLASK_APP=application.py \
  -e STATSD_ENABLED= \
  -e REDIS_ENABLED=${REDIS_ENABLED:-1} \
  -e REDIS_URL=$REDIS_URL \
  -e ADMIN_BASE_URL=${ADMIN_BASE_URL:-"http://host.docker.internal:6012"} \
  -e API_HOST_NAME=${API_HOST_NAME:-"http://host.docker.internal:6011"} \
  -e TEMPLATE_PREVIEW_API_HOST=${TEMPLATE_PREVIEW_API_HOST:-"http://host.docker.internal:6013"} \
  -e ANTIVIRUS_API_HOST=${ANTIVIRUS_API_HOST:-"http://host.docker.internal:6016"} \
  -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-$(aws configure get aws_access_key_id)} \
  -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-$(aws configure get aws_secret_access_key)} \
  -e SENTRY_ENABLED=${SENTRY_ENABLED:-0} \
  -e SENTRY_DSN=${SENTRY_DSN:-} \
  -e SENTRY_ERRORS_SAMPLE_RATE=${SENTRY_ERRORS_SAMPLE_RATE:-} \
  -e SENTRY_TRACES_SAMPLE_RATE=${SENTRY_TRACES_SAMPLE_RATE:-} \
  -e PORT=6012 \
  -p 6012:6012 \
  -v $(pwd):/home/vcap/app \
  ${DOCKER_ARGS} \
  ${DOCKER_IMAGE_NAME} \
  ${@}
