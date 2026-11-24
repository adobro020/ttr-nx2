# SPDX-License-Identifier: GPL-2.0-only
#
# x86-64 Linux reference: builds x86-64 test programs for Box64 and inspects
# the reference engine's headers and imports (Phase 2). On Apple silicon it
# runs under Rosetta or QEMU emulation; it is never performance-critical.
#
# Reproducibility: base image pinned by digest; apt reads a fixed
# snapshot.debian.org date.

# debian:12 (bookworm), multi-arch index digest
FROM --platform=linux/amd64 docker.io/library/debian@sha256:1d04200c2ece1d4d75a2a6f8e11ebce7d86a2ae28b34bb2c9cbb3ee9f4953e75

ARG DEBIAN_SNAPSHOT=20261120T000000Z

RUN set -eux; \
    rm -f /etc/apt/sources.list.d/debian.sources; \
    printf '%s\n' \
      "deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT} bookworm main" \
      "deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT} bookworm-updates main" \
      "deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/${DEBIAN_SNAPSHOT} bookworm-security main" \
      > /etc/apt/sources.list; \
    apt-get -o Acquire::Retries=5 update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      build-essential gcc g++ make binutils file \
      python3 ca-certificates; \
    rm -rf /var/lib/apt/lists/*

ENV HOME=/tmp
WORKDIR /work
