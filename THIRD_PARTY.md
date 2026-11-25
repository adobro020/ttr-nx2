# Third-party components

Kept current with every dependency change (CLAUDE.md rule 9). Exact commits
are in `docs/upstream-notes.md`. "Shipped" means its code or binaries end up
in a release zip.

## In the repository (git submodules, `third_party/`)

| Component | Upstream | Licence | Version | Shipped | Use |
|---|---|---|---|---|---|
| Chromium NX (gx, LKL glue) | https://github.com/shodowlo/chromium-nx | GPL-2.0 | v0.2.0 | yes, from Phase 3 | in-process Linux runtime |
| Box64 | https://github.com/ptitSeb/box64 | MIT | v0.4.4 | yes, from Phase 7 | x86-64 emulator for TTREngine |
| Simple TTR Launcher | https://github.com/mike406/Simple-TTR-Launcher | MIT | 4.0 | yes, unmodified, from Phase 5 | login and patching |

## Build tools (containers, not shipped)

| Component | Source | Licence | Version | Use |
|---|---|---|---|---|
| devkitA64, switch-tools, libnx deps | `devkitpro/devkita64` image | GPL (toolchain), mixed | image 20260219, devkitA64 r29.2-1 | NRO toolchain |
| libounce | https://github.com/ouncebrew/libounce | ISC (see its `LICENSE.md`, `LICENSES/`) | 20261117.1 | links into the NRO: shipped from the first release |
| OunceVK | https://github.com/ouncebrew/ouncevk | MIT and others (Mesa; see its `licenses/`) | 20261117.1 | linked from Phase 6: shipped |
| libkaihen | https://github.com/ouncebrew/kaihen (`libkaihen/`) | ISC | 20261117.1 | linked from Phase 1: shipped |
| ounce-devkit | https://github.com/ouncebrew/ounce-devkit | MIT | main @ 5e95759 | Dockerfile followed |
| Debian 12 | `debian:12` image + snapshot.debian.org 2026-11-20 | various DFSG | bookworm | bench and reference containers |
| gitleaks | https://github.com/gitleaks/gitleaks | MIT | 8.30.1 | secret scanning in hook and CI |
| CPython (python-build-standalone) | https://github.com/astral-sh/python-build-standalone | PSF-2.0 and others (in the tarball) | 3.12.16, release 20261110 | launcher on the arm64 bench (Phase 2) |
| Python packages for tests | PyPI, pinned in `tests/requirements.txt` | MIT / BSD / Apache-2.0 (each package) | see file | launcher contract tests, bench launcher |
| Mesa, Xvfb, strace, x11vnc, OpenAL Soft and X11 libraries | Debian 12 snapshot (above) | MIT / GPL-2.0 / LGPL | bookworm | reference runs of TTREngine (Phase 2) |

## Read for reference only (`third_party/reference/`, not in git, not shipped)

kaiHEN (GPL-2.0-only; `libkaihen/` ISC), ounce-examples (public domain mark),
ouncebrew/pacman (MIT). `tests/toolchain/hello/Makefile` is derived from
ounce-examples' application template (public domain mark).

## Not included

Toontown Rewritten game files, data and artwork. They are downloaded on the
user's device by the launcher and are never in this repository, CI or
releases.
