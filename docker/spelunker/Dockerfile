FROM ubuntu:22.04

ENV DEBIAN_FRONTEND noninteractive
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

LABEL org.opencontainers.image.source=https://github.com/woeplanet/woeoplanet-www-spelunker
LABEL org.opencontainers.image.description="The WoePlanet Spelunker"
LABEL org.opencontainers.image.licenses=BSD-3-Clause

RUN ln -fs /usr/share/zoneinfo/Europe/London /etc/localtime && \
    apt-get update && \
    apt-get install -y --no-install-recommends curl git openssh-client python3 \
        python3-dev python3-pip build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /service

COPY ./requirements.txt /service/requirements.txt
COPY ./VERSION /service/VERSION

RUN --mount=type=ssh mkdir -p "${HOME}"/.ssh && \
    chmod 0600 "${HOME}"/.ssh && \
    ssh-keyscan github.com >> "${HOME}"/.ssh/known_hosts && \
    mkdir /service/run && \
    pip install --no-cache-dir --upgrade -r /service/requirements.txt

COPY ./spelunker /service/spelunker
COPY ./static /service/static
COPY ./templates /service/templates

EXPOSE 80

HEALTHCHECK CMD curl --fail http://localhost:80/up || exit 1
CMD ["gunicorn", "spelunker.spelunker:app", "--bind", "0.0.0.0:80"]
