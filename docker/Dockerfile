FROM python:3.11-slim-bullseye as base

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libcurl4 \
    curl \
    && apt-get -y clean && \
    rm -rf /var/lib/apt/lists/* /tmp/*

WORKDIR /home/vcap/app


##### Frontend Build Image ###################################################
FROM ghcr.io/alphagov/notify/unit-tests-image:python311-node20 as frontend_build

ARG NOTIFY_ENVIRONMENT=development

WORKDIR /usr/frontend
COPY app app
COPY package-lock.json package.json gulpfile.js ./

RUN source ~/.nvm/nvm.sh \
    && npm ci --no-audit \
    && npm run build

##### Python Build Image #####################################################
FROM base AS python_build

RUN echo "Install OS dependencies for python app requirements" &&  \
    apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libxml2-dev libxslt-dev zlib1g-dev \
    && apt-get -y clean \
    && rm -rf /var/lib/apt/lists/* /tmp/*

COPY requirements.txt .

RUN echo "Installing python requirements" && \
    python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install -r requirements.txt

COPY . .
RUN make generate-version-file  # This file gets copied across

##### Production Image #######################################################
FROM base AS production

RUN groupadd -r notify && useradd -r -g notify -d /home/vcap notify && chown -R notify:notify /home/vcap
USER notify

RUN mkdir /home/vcap/logs

COPY --from=python_build --chown=root:root /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY --chown=notify:notify app app
COPY --chown=notify:notify application.py entrypoint.sh gunicorn_config.py ./
COPY --from=frontend_build --chown=notify:notify /usr/frontend/app/static app/static
COPY --from=frontend_build --chown=notify:notify /usr/frontend/app/templates app/templates
COPY --from=python_build --chown=notify:notify /home/vcap/app/app/version.py app/version.py

RUN python -m compileall . && \
    chown -R notify:notify /home/vcap/app && \
    chmod +x /home/vcap/app/entrypoint.sh

ENTRYPOINT [ "/home/vcap/app/entrypoint.sh" ]
CMD [ "web" ]

##### Test Image ##############################################################
FROM production as test

# If bumping this node version, also bump:
#   `.nvmrc` in notifications-admin
#   `concourse/docker/unit-tests-image.Dockerfile` in notifications-aws
# Keep NVM_VERSION in sync as well.
ARG NVM_VERSION=0.39.7
ARG NODE_VERSION=20.10.0

USER root

RUN echo "Install OS dependencies for test build" && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      sudo \
      make \
      curl \
      libxml2-dev libxslt-dev zlib1g-dev \
      git && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/* /tmp/*
RUN usermod -aG sudo notify
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER notify

ENV HOME=/home/vcap
ENV NVM_DIR /home/vcap/.nvm
ENV NODE_PATH $NVM_DIR/v$NODE_VERSION/lib/node_modules
ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH

COPY .nvmrc .nvmrc
RUN echo "Installing nvm and NodeJS v${NODE_VERSION}" && \
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v${NVM_VERSION}/install.sh | bash && \
    . ${NVM_DIR}/nvm.sh && \
    nvm install

# Copying to overwrite is faster than RUN chown notify:notify ...
COPY --from=python_build --chown=notify:notify /opt/venv /opt/venv

# Make sure the app/ directory is there so that "make bootstrap" can create app/version.py
RUN mkdir -p app

# Install dev/test requirements
COPY --chown=notify:notify Makefile requirements.txt requirements_for_test.txt package-lock.json package.json gulpfile.js ./
RUN make bootstrap

COPY --chown=notify:notify . .

CMD [ "web-local" ]
