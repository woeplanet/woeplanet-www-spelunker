SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -O extglob -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

.DEFAULT_GOAL := help

VAULT := homelab
VERSION := $(shell cat ./VERSION)
COMMIT_HASH := $(shell git log -1 --pretty=format:"sha-%h")
PLATFORMS := "linux/arm/v7,linux/arm64/v8,linux/amd64"

BUILD_FLAGS ?=

ifndef HOMELAB_OP_SERVICE_ACCOUNT_TOKEN
$(error HOMELAB_OP_SERVICE_ACCOUNT_TOKEN is not set in your environment)
endif

HADOLINT_IMAGE := hadolint/hadolint

.PHONY: help
help: ## Show this help message
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' Makefile

.PHONY: dotenv
dotenv: .env	## Setup build secrets in .env files

.env: .env.template
	OP_SERVICE_ACCOUNT_TOKEN=${HOMELAB_OP_SERVICE_ACCOUNT_TOKEN} VAULT=$(VAULT) op inject --force --in-file $< --out-file $@

# Wrap the build in a check for an existing .env file
ifeq ($(shell test -f .env; echo $$?), 0)
include .env
ENVVARS := $(shell sed -ne 's/ *\#.*$$//; /./ s/=.*$$// p' .env )
$(foreach var,$(ENVVARS),$(eval $(shell echo export $(var)="$($(var))")))

.DEFAULT_GOAL := help

VERSION := $(shell cat ./VERSION)
COMMIT_HASH := $(shell git log -1 --pretty=format:"sha-%h")

BUILD_FLAGS ?= 

SPELUNKER := spelunker
SPELUNKER_BUILDER := $(SPELUNKER)-builder
SPELUNKER_REPO := ${GITHUB_REGISTRY}/woeplanet
SPELUNKER_IMAGE := ${SPELUNKER}
SPELUNKER_DOCKERFILE := ./docker/${SPELUNKER}/Dockerfile

HADOLINT_IMAGE := hadolint/hadolint

.PHONY: lint
lint: lint-pylint lint-flake8 lint-docker	## Run all linters on the code base

.PHONY: lint-pylint
lint-pylint:	## Run pylint on the code base
	pylint --verbose -j 4 --recursive yes spelunker

.PHONY: lint-flake8
lint-flake8:	## Run flake8 on the code base
	flake8 -j 4 spelunker

.PHONY: lint-docker
lint-docker: lint-compose lint-dockerfiles ## Lint all Docker related files

.PHONY: lint-compose
lint-compose:	## Lint docker-compose.yml
	docker compose -f docker-compose.yml config 1> /dev/null

.PHONY: lint-dockerfiles
.PHONY: _lint-dockerfiles ## Lint all Dockerfiles
lint-dockerfiles: lint-${SPELUNKER}-dockerfile

.PHONY: lint-${SPELUNKER}-dockerfile
lint-${SPELUNKER}-dockerfile:
	$(MAKE) _lint-dockerfile -e BUILD_DOCKERFILE="${SPELUNKER_DOCKERFILE}"

BUILD_TARGETS := build-assets build-spelunker

.PHONY: build
build: $(BUILD_TARGETS) ## Build all images

REBUILD_TARGETS := rebuild-spelunker

.PHONY: rebuild
rebuild: $(REBUILD_TARGETS) ## Rebuild all images (no cache)

RELEASE_TARGETS := release-spelunker

.PHONY: release
release: $(RELEASE_TARGETS)	## Tag and push all images

# spelunker targets

.PHONY: build-assets
build-assets:
	yarn install
	grunt build

build-spelunker: build-assets	## Build the spelunker image
	$(MAKE) _build-image \
		-e BUILD_DOCKERFILE=./docker/$(SPELUNKER)/Dockerfile \
		-e BUILD_IMAGE=$(SPELUNKER_IMAGE)

rebuild-spelunker: build-assets	## Rebuild the spelunker image (no cache)
	$(MAKE) _build-image \
		-e BUILD_DOCKERFILE=./docker/$(SPELUNKER)/Dockerfile \
		-e BUILD_IMAGE=$(SPELUNKER_IMAGE) \
		-e BUILD_FLAGS="--no-cache"

release-spelunker: build-spelunker	## Tag and push the spelunker image
	$(MAKE) _tag-image \
		-e BUILD_IMAGE=$(SPELUNKER_IMAGE) \
		-e BUILD_TAG=$(COMMIT_HASH)
	$(MAKE) _tag-image \
		-e BUILD_IMAGE=$(SPELUNKER_IMAGE) \
		-e BUILD_TAG=$(VERSION)

.PHONY: up
up: repo_login	## Bring the container stack up
	docker compose up -d

.PHONY: down
down:	## Bring the container stack down
	docker compose down

.PHONY: pull
pull:	## Pull all current Docker images
	docker compose pull

.PHONY: restart
restart: down up	## Restart the container stack

.PHONY: _lint-dockerfile
_lint-dockerfile:
	docker run --rm -i -e HADOLINT_IGNORE=DL3008,DL3018,DL3003 ${HADOLINT_IMAGE} < ${BUILD_DOCKERFILE}

.PHONY: init-builder
init-builder:
	docker buildx inspect $(SPELUNKER_BUILDER) > /dev/null 2>&1 || \
		docker buildx create --name $(SPELUNKER_BUILDER) --bootstrap --use

.PHONY: _build-image
_build-image: repo-login
	docker buildx build --platform=$(PLATFORMS) \
		--file ${BUILD_DOCKERFILE} \
		--push \
		--tag ${SPELUNKER_REPO}/${BUILD_IMAGE}:latest \
		--provenance=false \
		--build-arg VERSION=${VERSION} \
		--build-arg UBUNTU_VERSION=${UBUNTU_VERSION} \
		--ssh default \
		$(BUILD_FLAGS) .

.PHONY: _tag-image
_tag-image: repo-login
	docker buildx imagetools create ${SPELUNKER_REPO}/$(BUILD_IMAGE):latest \
		--tag ${SPELUNKER_REPO}/$(BUILD_IMAGE):$(BUILD_TAG)

.PHONY: repo-login
repo-login:
	echo "${GITHUB_PAT}" | docker login ${GITHUB_REGISTRY} -u ${GITHUB_USER} --password-stdin

# No .env file; fail the build
else
.DEFAULT:
	$(error Cannot find a .env file; run make dotenv)
endif
