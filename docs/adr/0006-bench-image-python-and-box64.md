# 0006 — Bench image: CPython 3.12 from python-build-standalone, Box64 staged per run

Date: 2026-11-24. Status: accepted (Phase 2).

## Context

The launcher needs Python ≥ 3.12 (nested same-quote f-strings), and
`docker/bench-arm64` is Debian 12, which ships 3.11. The bench also needs X,
Mesa and tracing tools for the reference runs, and a stock Box64.

## Options

1. Build CPython 3.12 from source in the Dockerfile. Slow, more to pin.
2. Debian 13 base. Ships 3.13, not 3.12; changes every other package.
3. A SHA-256-checked python-build-standalone tarball (astral-sh,
   `20261110`, CPython 3.12.16, aarch64 glibc), pip packages pinned by
   version from `tests/requirements.txt`.

## Decision

Option 3. Box64 is built from the pinned submodule out of tree
(`build/box64-bench`, `-DARM64=ON -DARM_DYNAREC=ON`, RelWithDebInfo) and
installed with `DESTDIR` into `build/box64-bench/stage` because the
container is discarded after each run. Native arm64 libraries Box64 wraps
(X11 family, GLVND `libOpenGL`/`libGLX`, Mesa, OpenAL, ALSA, PulseAudio
client) come from the same Debian snapshot.

## Consequences

- CPython for Phase 4's rootfs is a separate choice (it must run on gx); this
  one only runs the launcher on the bench.
- Box64's version banner shows the superproject's commit, not Box64's: its
  CMake runs `git rev-parse` in the build directory, which is inside this
  repository. The real commit is `2f130fa` (v0.4.4). Cosmetic; noted in
  `docs/upstream-notes.md`.
- Box64's build writes `src/git_head.h` and `src/dynacache_hashes.h` into the
  submodule; both are ignored by the submodule's `.gitignore`, so its
  status stays clean.
