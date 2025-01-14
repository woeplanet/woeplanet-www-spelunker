ARG UBUNTU_VERSION=24.04
ARG VERSION
FROM ubuntu:${UBUNTU_VERSION}

ARG UBUNTU_VERSION
ARG VERSION

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN <<EOT
ln -fs /usr/share/zoneinfo/Europe/London /etc/localtime
apt-get update -qy
apt-get install -qyy \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    curl \
    git \
    openssh-client \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    build-essential
apt-get clean && \
rm -rf /var/lib/apt/lists/*
EOT

WORKDIR /service

COPY ./requirements.txt /service/requirements.txt
COPY ./VERSION /service/VERSION

ENV VIRTUAL_ENV=/service/venv
RUN python3 -m venv ${VIRTUAL_ENV}
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
ENV PYTHONPATH=/service

RUN --mount=type=ssh <<EOT
mkdir -p "${HOME}"/.ssh
chmod 0600 "${HOME}"/.ssh
ssh-keyscan github.com >> "${HOME}"/.ssh/known_hosts
mkdir /service/run
pip install --no-cache-dir --upgrade -r /service/requirements.txt
EOT

COPY ./spelunker /service/spelunker
COPY ./static /service/static
COPY ./templates /service/templates

EXPOSE 80

LABEL org.opencontainers.image.source=https://github.com/woeplanet/woeoplanet-www-spelunker
LABEL org.opencontainers.image.url=https://github.com/woeplanet/woeoplanet-www-spelunker/tree/master#readme
LABEL org.opencontainers.image.authors="Gary Gale <gary@vicchi.org>"
LABEL org.opencontainers.image.version=${VERSION}
LABEL org.opencontainers.image.revision=${VERSION}
LABEL org.opencontainers.image.licenses=BSD-3-Clause
LABEL org.opencontainers.image.description="The WoePlanet Spelunker"
LABEL org.opencontainers.image.title="WoePlanet Spelunker"
LABEL org.opencontainers.image.base.name=docker.io/ubuntu:${UBUNTU_VERSION}

HEALTHCHECK CMD curl --fail http://localhost:80/up || exit 1
CMD ["gunicorn", "spelunker.spelunker:app", "--bind", "0.0.0.0:80"]
