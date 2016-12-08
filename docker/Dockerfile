FROM python:3.4-slim

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

ENV PYTHONUNBUFFERED=1 \
	DEBIAN_FRONTEND=noninteractive \
	NODEJS_VERSION=6.3.1-1nodesource1~jessie1

RUN \
	echo "Install base packages" \
	&& ([ -z "$HTTP_PROXY" ] || echo "Acquire::http::Proxy \"${HTTP_PROXY}\";" > /etc/apt/apt.conf.d/99HttpProxy) \
	&& apt-get update \
	&& apt-get install -y --no-install-recommends \
		apt-transport-https \
		make \
		curl \
		git \
		build-essential \
		libxml2-dev \
		libxslt-dev \
		zlib1g-dev \
		zip \
		rlwrap \
		python-dev \
		libffi-dev \
		libssl-dev \
		libexif-dev \
		libfreetype6-dev \
		libjpeg-dev \
		liblcms2-2 \
		libtiff5-dev \
		zlib1g-dev \
		libpango1.0-dev \
		libcairo2-dev \
		libmagickwand-dev \
		ghostscript \
		jq \

	&& echo "Install nodejs" \
	&& cd /tmp \
	&& curl -x "$HTTP_PROXY" -sSLO https://deb.nodesource.com/node_6.x/pool/main/n/nodejs/nodejs_${NODEJS_VERSION}_amd64.deb \
	&& dpkg -i /tmp/nodejs_${NODEJS_VERSION}_amd64.deb \

	&& echo "Clean up" \
	&& rm -rf /var/lib/apt/lists/* /tmp/*

RUN \
	echo "Install global pip packages" \
	&& pip install \
		virtualenv \
		awscli \
		wheel

RUN \
	echo "Install Cloud Foundry CLI" \
	&& curl -sSL "https://cli.run.pivotal.io/stable?release=debian64&source=github" -o /tmp/cloudfoundry-cli.deb \
	&& dpkg -i /tmp/cloudfoundry-cli.deb \
	&& cf install-plugin -r CF-Community -f "autopilot" \
	&& cf install-plugin -r CF-Community -f "blue-green-deploy" \
	&& cf install-plugin -r CF-Community -f "antifreeze"

WORKDIR /var/project
