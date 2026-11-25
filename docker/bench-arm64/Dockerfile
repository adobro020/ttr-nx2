# SPDX-License-Identifier: GPL-2.0-only
#
# arm64 Linux bench: builds LKL, the gx PC bench, the guest shims, Box64 and
# rootfs.ext4 (Phases 3, 4, 7, 8). Native speed on Apple silicon.
# Phase 2 adds what the reference run of TTREngine under stock Box64 needs:
# a virtual X server with Mesa software GL, tracing tools, the native arm64
# libraries Box64 wraps, and CPython 3.12 with the launcher's packages.
#
# Reproducibility: the base image is pinned by digest and apt reads a fixed
# snapshot.debian.org date, so the same package versions install every time.
# CPython is a SHA-256-checked python-build-standalone tarball; pip packages
# are pinned in requirements.txt (a copy of tests/requirements.txt, checked
# identical by `make lint`).

# debian:12 (bookworm), multi-arch index digest
FROM --platform=linux/arm64 docker.io/library/debian@sha256:1d04200c2ece1d4d75a2a6f8e11ebce7d86a2ae28b34bb2c9cbb3ee9f4953e75

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
      build-essential gcc g++ make cmake ninja-build pkg-config \
      flex bison bc libelf-dev libssl-dev \
      python3 python3-venv python3-pip \
      e2fsprogs \
      git ca-certificates curl xz-utils file; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      xvfb xauth x11-utils x11-apps netpbm mesa-utils \
      libgl1 libglx-mesa0 libgl1-mesa-dri libegl1 libgles2 libglu1-mesa \
      libx11-6 libxext6 libxrender1 libxrandr2 libxcursor1 libxi6 \
      libxinerama1 libxxf86vm1 libxss1 libxfixes3 libxcomposite1 libxkbcommon0 \
      libasound2 libasound2-plugins alsa-utils libopenal1 libpulse0 \
      libsdl2-2.0-0 libfreetype6 libfontconfig1 libpng16-16 libjpeg62-turbo \
      zlib1g libbz2-1.0 liblzma5 libssl3 libcurl4 libstdc++6 libgcc-s1 \
      strace apitrace apitrace-tracers time procps psmisc; \
    rm -rf /var/lib/apt/lists/*

# CPython 3.12 for the launcher (it needs >= 3.12; bookworm has 3.11).
ARG PBS_RELEASE=20261110
ARG PY_VERSION=3.12.16
ARG PY_SHA256=4792f81750282597fb2a3389fe18b945ed2ba6aad5e45ad406d122c58cb33081
COPY requirements.txt /opt/requirements.txt
RUN set -eux; \
    tgz="cpython-${PY_VERSION}+${PBS_RELEASE}-aarch64-unknown-linux-gnu-install_only.tar.gz"; \
    curl -fsSL --retry 5 -o "/tmp/${tgz}" \
      "https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_RELEASE}/${tgz}"; \
    echo "${PY_SHA256}  /tmp/${tgz}" | sha256sum -c -; \
    mkdir -p /opt/python3.12; \
    tar -xzf "/tmp/${tgz}" -C /opt/python3.12 --strip-components=1; \
    rm "/tmp/${tgz}"; \
    /opt/python3.12/bin/python3.12 -m pip install --no-cache-dir -r /opt/requirements.txt; \
    ln -s /opt/python3.12/bin/python3.12 /usr/local/bin/python3.12

# x11vnc lets the human watch the virtual screen in the logged-in reference
# run (docs/recon/human-run.md); libXxf86dga is dlopen()ed by the engine.
RUN set -eux; \
    apt-get -o Acquire::Retries=5 update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      x11vnc libxxf86dga1; \
    rm -rf /var/lib/apt/lists/*

# ALSA: route the default device to a null sink so engines that open audio
# get a working device without hardware (Phase 2 reference runs).
RUN printf '%s\n' 'pcm.!default { type null }' > /etc/asound.conf

ENV HOME=/tmp
WORKDIR /work
