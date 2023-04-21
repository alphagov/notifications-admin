FROM ghcr.io/alphagov/notify/unit-tests-image:python39-node16x-npm831 as frontend-build

ARG NOTIFY_ENVIRONMENT=development

WORKDIR /usr/frontend
COPY app app
COPY package-lock.json package.json gulpfile.js ./

RUN source ~/.nvm/nvm.sh \
    && npm ci --no-audit \
    && npm run build

FROM python:3.9-slim-bullseye as python-build

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && apt-get -y clean \
    && rm -rf /var/lib/apt/lists/* /tmp/*

RUN groupadd -r notify && useradd -r -g notify notify

WORKDIR /home/vcap/app

COPY requirements.txt ./

RUN echo "Installing python dependencies" \
    && pip install -r requirements.txt

COPY app app

# This should fail if there's no version present
# run `make generate-version-file` for local dev
COPY app/version.py app/version.py

COPY application.py gunicorn_config.py ./
COPY --from=frontend-build /usr/frontend/app/static app/static
COPY --from=frontend-build /usr/frontend/app/templates app/templates

USER notify
