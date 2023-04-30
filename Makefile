SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -O extglob -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

ifeq ($(.DEFAULT_GOAL),)
ifneq ($(shell test -f .env; echo $$?), 0)
$(error Cannot find a .env file; copy .env.sample and customise)
endif
endif

# Wrap the build in a check for an existing .env file
ifeq ($(shell test -f .env; echo $$?), 0)
include .env
ENVVARS := $(shell sed -ne 's/ *\#.*$$//; /./ s/=.*$$// p' .env )
$(foreach var,$(ENVVARS),$(eval $(shell echo export $(var)="$($(var))")))

.DEFAULT_GOAL := help

VERSION := $(shell cat ./VERSION)
COMMIT_HASH := $(shell git log -1 --pretty=format:"sha-%h")

BUILD_FLAGS ?= 

SPELUNKER_SERVICE := spelunker
SPELUNKER_SERVICE_REPO := ${GITHUB_REGISTRY}/woeplanet
SPELUNKER_SERVICE_IMAGE := ${SPELUNKER_SERVICE}
SPELUNKER_SERVICE_DOCKERFILE := ./docker/${SPELUNKER_SERVICE}/Dockerfile

HADOLINT_IMAGE := hadolint/hadolint

.PHONY: help
help: ## Show this help message
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' Makefile

.PHONY: lint
lint: lint-pylint lint-flake8	## Run all linters on the code base

.PHONY: lint-pylint
lint-pylint:	## Run pylint on the code base
	pylint --verbose -j 4 --reports yes --recursive yes spelunker

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
lint-dockerfiles: lint-${SPELUNKER_SERVICE}-dockerfile

.PHONY: lint-${SPELUNKER_SERVICE}-dockerfile
lint-${SPELUNKER_SERVICE}-dockerfile:
	$(MAKE) _lint_dockerfile -e BUILD_DOCKERFILE="${SPELUNKER_SERVICE_DOCKERFILE}"

BUILD_TARGETS := build_spelunker_service

.PHONY: build
build: $(BUILD_TARGETS) ## Build all images

REBUILD_TARGETS := rebuild_spelunker_service

.PHONY: rebuild
rebuild: $(REBUILD_TARGETS) ## Rebuild all images (no cache)

RELEASE_TARGETS := release_spelunker_service

.PHONY: release
release: $(RELEASE_TARGETS)	## Tag and push all images

# spelunker-service targets

build_spelunker_service:	## Build the spelunker_service image
	$(MAKE) _build_image \
		-e BUILD_DOCKERFILE=./docker/$(SPELUNKER_SERVICE)/Dockerfile \
		-e BUILD_IMAGE=$(SPELUNKER_SERVICE_IMAGE)
	$(MAKE) _tag_image \
		-e BUILD_IMAGE=$(SPELUNKER_SERVICE_IMAGE) \
		-e BUILD_TAG=latest

rebuild_spelunker_service:	## Rebuild the spelunker_service image (no cache)
	$(MAKE) _build_image \
		-e BUILD_DOCKERFILE=./docker/$(SPELUNKER_SERVICE)/Dockerfile \
		-e BUILD_IMAGE=$(SPELUNKER_SERVICE_IMAGE) \
		-e BUILD_FLAGS="--no-cache"
	$(MAKE) _tag_image \
		-e BUILD_IMAGE=$(SPELUNKER_SERVICE_IMAGE) \
		-e BUILD_TAG=latest

release_spelunker_service: build_spelunker_service repo_login	## Tag and push spelunker_service image
	$(MAKE) _release_image \
		-e BUILD_IMAGE=$(SPELUNKER_SERVICE_IMAGE)

.PHONY: up
up: repo_login	## Bring the Spelunker container stack up
	docker compose up -d

.PHONY: down
down: _env_check repo_login	## Bring the Spelunker container stack down
	docker compose  down

.PHONY: restart
restart: down up	## Restart the Spelunker container stack

.PHONY: destroy
destroy:	## Bring the Spelunker container stack down (removing volumes)
	docker compose down -v

.PHONY: _lint_dockerfile
_lint_dockerfile:
	docker run --rm -i -e HADOLINT_IGNORE=DL3008 ${HADOLINT_IMAGE} < ${BUILD_DOCKERFILE}

.PHONY: _build_image
_build_image:
	DOCKER_BUILDKIT=1 docker build --file ${BUILD_DOCKERFILE} --tag ${BUILD_IMAGE} --ssh default $(BUILD_FLAGS) .

.PHONY: _release_image
_release_image:
	$(MAKE) _tag_image \
		-e BUILD_IMAGE=$(BUILD_IMAGE) \
		-e BUILD_TAG=$(VERSION)
	$(MAKE) _tag_image \
		-e BUILD_IMAGE=$(BUILD_IMAGE) \
		-e BUILD_TAG=$(COMMIT_HASH)
	$(MAKE) _registry_tag_image \
		-e BUILD_IMAGE=$(BUILD_IMAGE) \
		-e BUILD_TAG=latest
	$(MAKE) _registry_tag_image \
		-e BUILD_IMAGE=$(BUILD_IMAGE) \
		-e BUILD_TAG=$(VERSION)
	$(MAKE) _registry_tag_image \
		-e BUILD_IMAGE=$(BUILD_IMAGE) \
		-e BUILD_TAG=$(COMMIT_HASH)

	docker push ${SPELUNKER_SERVICE_REPO}/$(BUILD_IMAGE):latest
	docker push ${SPELUNKER_SERVICE_REPO}/$(BUILD_IMAGE):$(VERSION)
	docker push ${SPELUNKER_SERVICE_REPO}/$(BUILD_IMAGE):$(COMMIT_HASH)

.PHONY: _tag_image
_tag_image:
	docker tag ${BUILD_IMAGE} ${BUILD_IMAGE}:${BUILD_TAG}

.PHONY: _registry_tag_image
_registry_tag_image:
	docker tag ${BUILD_IMAGE} ${SPELUNKER_SERVICE_REPO}/${BUILD_IMAGE}:${BUILD_TAG}

.PHONY: repo_login
repo_login:
	echo "${GITHUB_PAT}" | docker login ${GITHUB_REGISTRY} -u ${GITHUB_USER} --password-stdin

# No .env file; fail the build
else
.DEFAULT:
	$(error Cannot find a .env file; copy .env.sample and customise)
endif
