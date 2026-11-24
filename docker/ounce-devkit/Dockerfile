# SPDX-License-Identifier: GPL-2.0-only
#
# Switch 2 devkit for building the NRO: devkitPro's devkitA64 image plus
# libounce, OunceVK and libkaihen. Follows ouncebrew/ounce-devkit's
# Dockerfile (pinned in docs/upstream-notes.md), with one change for
# reproducibility: the [ounce] pacman repository serves only its newest
# release, so instead of install.sh we install the exact package files from
# each library's GitHub release and check their SHA-256 (ADR 0002).
#
# devkitpro/devkita64 publishes linux/amd64 and linux/arm64. The digest below
# is the multi-arch index, so the build is native on Apple silicon and on
# GitHub's x86-64 runners alike.
#
# All of libounce's dependencies (devkitA64 r29.2-1, devkita64-cmake,
# switch-cmake, switch-tools, dkp-toolchain-vars, switch-zlib) are already in
# this base image; nothing is pulled from devkitPro's rolling repositories.

# devkitpro/devkita64:20260219
FROM docker.io/devkitpro/devkita64@sha256:1fc388c3a0d34bd2045a6dadcb1020e069d5f876a187fd705de14b4440c00282

ARG OUNCE_RELEASE=20261117.1
ARG LIBOUNCE_SHA256=74336b088305dabb4c12a6060cb7fbf38936e137a0f2b2abc86413b561264810
ARG OUNCEVK_SHA256=061dd6a172255e272c5258578745533db043aff05e8b321d8a86850fd702ffeb
ARG LIBKAIHEN_SHA256=9b53139a92ca8b7b1d3c4249a5f7a0987f089f7a9b74e6193889eef9df820606

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN set -eux; \
    base="https://github.com/ouncebrew"; \
    mkdir /tmp/pkgs; cd /tmp/pkgs; \
    curl -fsSLO "$base/libounce/releases/download/${OUNCE_RELEASE}/libounce-${OUNCE_RELEASE}-1-any.pkg.tar.zst"; \
    curl -fsSLO "$base/ouncevk/releases/download/${OUNCE_RELEASE}/ouncevk-${OUNCE_RELEASE}-1-any.pkg.tar.zst"; \
    curl -fsSLO "$base/kaihen/releases/download/${OUNCE_RELEASE}/libkaihen-${OUNCE_RELEASE}-1-any.pkg.tar.zst"; \
    printf '%s  %s\n' \
      "$LIBOUNCE_SHA256"  "libounce-${OUNCE_RELEASE}-1-any.pkg.tar.zst" \
      "$OUNCEVK_SHA256"   "ouncevk-${OUNCE_RELEASE}-1-any.pkg.tar.zst" \
      "$LIBKAIHEN_SHA256" "libkaihen-${OUNCE_RELEASE}-1-any.pkg.tar.zst" \
      | sha256sum -c -; \
    dkp-pacman -U --noconfirm --needed \
      "libounce-${OUNCE_RELEASE}-1-any.pkg.tar.zst" \
      "ouncevk-${OUNCE_RELEASE}-1-any.pkg.tar.zst" \
      "libkaihen-${OUNCE_RELEASE}-1-any.pkg.tar.zst"; \
    rm -rf /tmp/pkgs; \
    dkp-pacman -Q libounce ouncevk libkaihen devkitA64 switch-tools

ENV DEVKITPRO=/opt/devkitpro \
    DEVKITA64=/opt/devkitpro/devkitA64 \
    HOME=/tmp
WORKDIR /work
