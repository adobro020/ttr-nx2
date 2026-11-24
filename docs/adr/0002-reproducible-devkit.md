# 0002 — Install the Switch 2 devkit from pinned release assets

Date: 2026-11-24. Status: accepted (Phase 0).

## Context

ounce-devkit's Dockerfile runs `install.sh`, which adds the `[ounce]` pacman
repository and installs `libounce ouncevk libkaihen`. That repository serves
exactly one version of each package (ouncebrew/pacman `sources`), and it
changes whenever upstream bumps a pin. Building the same commit next week
would silently produce an NRO against different libraries, which breaks the
rule that every release is reproducible from tagged source.

## Options

1. Follow upstream: `install.sh` from `[ounce]`. Simple; not reproducible.
2. Pin the image digest only. The pacman step still floats.
3. Download each package file from its library's GitHub release at a pinned
   tag, check SHA-256 against values in the Dockerfile, install with
   `dkp-pacman -U`.
4. Build libounce, OunceVK and libkaihen from source in the container.

## Decision

Option 3. The base image `devkitpro/devkita64:20260219` is pinned by its
multi-arch index digest and already contains every dependency libounce
declares, so no rolling repository is consulted. glslang-tools (from apt in
upstream's Dockerfile) is left out until Vulkan shaders are needed.
Option 4 stays the fallback if release assets disappear.

## Consequences

- Same Dockerfile, same libraries, on the Mac (arm64, native) and on CI
  (amd64): the base image publishes both.
- Bumping the devkit is an explicit change of four lines (`OUNCE_RELEASE`
  and three hashes) plus a note in `docs/upstream-notes.md` and a re-probe.
- We bypass the `[ounce]` signing key; integrity rests on the SHA-256 values
  taken from the repository database and the GitHub release digests, which
  matched on 2026-11-24.
- The Makefile tags images by the Dockerfile's blob id, so a changed
  Dockerfile never reuses a stale image.
