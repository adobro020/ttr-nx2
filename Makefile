# SPDX-License-Identifier: GPL-2.0-only
#
# TTR NX2 (unofficial) - one entry point for every build and test.
# Console and guest builds run in containers (docker/); see CLAUDE.md.

SHELL       := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
ROOT        := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
DOCKER      ?= docker
PYTHON      ?= python3.12
CI          ?=

# Image tags follow the Dockerfile's git blob id, so editing a Dockerfile
# builds a new image instead of reusing a stale one.
image_tag = $(shell git -C $(ROOT) hash-object docker/$(1)/Dockerfile | cut -c1-12)
DEVKIT_IMAGE := ttr-nx2/ounce-devkit:$(call image_tag,ounce-devkit)
BENCH_IMAGE  := ttr-nx2/bench-arm64:$(call image_tag,bench-arm64)
REF_IMAGE    := ttr-nx2/ref-amd64:$(call image_tag,ref-amd64)

# Run as the invoking user so build output is not owned by root on Linux.
DOCKER_RUN = $(DOCKER) run --rm --user "$$(id -u):$$(id -g)" -v "$(ROOT):/work" -w /work

HELLO_DIR := tests/toolchain/hello

.PHONY: help doctor hooks reference images image-devkit image-bench image-ref \
        hello nro bench test test-nx2like rootfs deploy logs \
        guardrails lint clean

help:
	@echo "make doctor        check this machine (CI=1 for the CI variant)"
	@echo "make hooks         install the guard-rail pre-commit hook"
	@echo "make hello         build build/hello.nro in the devkit container"
	@echo "make test          unit tests (macOS tier)"
	@echo "make lint          shellcheck and Python compile checks"
	@echo "make guardrails    game-file / launcher-pin / secret checks over the tree"
	@echo "make images        build all three containers"
	@echo "make reference     clone read-only upstream sources into third_party/reference"
	@echo "make nro | bench | test-nx2like | rootfs | deploy IP=.. | logs IP=..  (later phases)"

doctor:
	@tools/doctor.sh $(if $(CI),--ci,)

hooks:
	git -C $(ROOT) config core.hooksPath .githooks
	@echo "pre-commit hook installed (.githooks/pre-commit)"

reference:
	tools/fetch-reference.sh

# --- containers ---------------------------------------------------------------
images: image-devkit image-bench image-ref

image-devkit:
	@$(DOCKER) image inspect $(DEVKIT_IMAGE) >/dev/null 2>&1 || \
	  $(DOCKER) build -t $(DEVKIT_IMAGE) docker/ounce-devkit

image-bench:
	@$(DOCKER) image inspect $(BENCH_IMAGE) >/dev/null 2>&1 || \
	  $(DOCKER) build --platform linux/arm64 -t $(BENCH_IMAGE) docker/bench-arm64

image-ref:
	@$(DOCKER) image inspect $(REF_IMAGE) >/dev/null 2>&1 || \
	  $(DOCKER) build --platform linux/amd64 -t $(REF_IMAGE) docker/ref-amd64

# --- builds -------------------------------------------------------------------
hello: image-devkit
	@$(DOCKER_RUN) $(DEVKIT_IMAGE) test -f $(HELLO_DIR)/Makefile || \
	  { echo "hello: $(ROOT) is not visible in the container; share it with the container VM (docs/dev-setup-macos.md)" >&2; exit 1; }
	$(DOCKER_RUN) -w /work/$(HELLO_DIR) $(DEVKIT_IMAGE) make
	@mkdir -p build
	cp $(HELLO_DIR)/hello.nro build/hello.nro
	@xxd -s 0x10 -l 16 build/hello.nro
	@[ "$$(dd if=build/hello.nro bs=1 skip=16 count=4 2>/dev/null)" = NRO0 ] || \
	  { echo "hello: build/hello.nro has no NRO0 magic at 0x10" >&2; exit 1; }
	@echo "hello: build/hello.nro OK"

# --- tests --------------------------------------------------------------------
test:
	$(PYTHON) -m unittest discover -s tests/unit -t . -v

guardrails:
	python3 tools/guardrails/check.py --all
	gitleaks git --redact --no-banner --config .gitleaks.toml .

lint:
	shellcheck tools/*.sh tools/github/*.sh .githooks/pre-commit
	$(PYTHON) -m py_compile tools/guardrails/check.py tests/unit/*.py

# --- later phases ---------------------------------------------------------------
nro bench test-nx2like rootfs deploy logs:
	@echo "make $@: not implemented in this phase" >&2
	@exit 1

clean:
	rm -rf build $(HELLO_DIR)/build
	rm -f $(HELLO_DIR)/hello.nro $(HELLO_DIR)/hello.nacp $(HELLO_DIR)/hello.elf
