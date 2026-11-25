# SPDX-License-Identifier: GPL-2.0-only
#
# x86-64 Linux reference: builds x86-64 test programs for Box64 and inspects
# the reference engine's headers and imports (Phase 2). The x86-64 runtime
# libraries TTREngine names in DT_NEEDED are installed so that
# tools/ref/imports_by_lib.py can say which library provides each import. On Apple silicon it
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
      python3 ca-certificates \
      libopengl0 libglx0 libgl1 libx11-6 libxext6 libxcursor1 libxi6 \
      libxrandr2 libxxf86dga1 libatomic1 libstdc++6 libasound2 libpulse0; \
    rm -rf /var/lib/apt/lists/*

ENV HOME=/tmp
WORKDIR /work
