FROM node:16-alpine as frontend-build

WORKDIR /usr/frontend
COPY app app
COPY package-lock.json package.json gulpfile.js ./

RUN npm install \
    && npm run build

FROM python:3.9-slim-bullseye as python-build

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && apt-get -y clean \
    && rm -rf /var/lib/apt/lists/* /tmp/*

RUN pip install --upgrade pip
RUN groupadd -r notify && useradd -r -g notify notify

WORKDIR /home/vcap/app

COPY requirements.txt ./

RUN echo "Installing python dependencies" \
    && pip install -r requirements.txt

COPY app app
COPY application.py gunicorn_config.py ./
COPY --from=frontend-build /usr/frontend/app/static app/static

USER notify
