# Upstream notes

Every upstream this project depends on or reads, with the exact commit, its
licence and the date it was pinned, and what we relied on from it. Before
using an upstream API, read it at the pinned commit and add a line here
(CLAUDE.md, "Knowledge you should distrust").

## Submodules (`third_party/`, checked by `git submodule status`)

| Path | Upstream | Tag | Commit | Commit date | Licence | Pinned |
|---|---|---|---|---|---|---|
| `third_party/chromium-nx` | shodowlo/chromium-nx | v0.2.0 | `8652bc7fdf3f26989377cf8e07c51fb3bf057a2e` | 2026-11-19 | GPL-2.0 (`LICENSE`) | 2026-11-24 |
| `third_party/box64` | ptitSeb/box64 | v0.4.4 | `2f130fab1d6e1a4ee8a71dc60cfdfcc839ad192a` | release 2026-08-02 | MIT (`LICENSE`) | 2026-11-24 |
| `third_party/Simple-TTR-Launcher` | mike406/Simple-TTR-Launcher | 4.0 | `af80b26bbf06cbd9d25c53b225003bd310c00252` | 2026-08-16 (release 2026-08-17) | MIT (`LICENSE`) | 2026-11-24 |

Why these versions:

- **Chromium NX v0.2.0** is the release that added Switch 2 support (tested
  by its author on firmware 23.0.1 with kaiHEN 20261117.1). `main` is 3
  commits ahead, adding only a logo.
- **Box64 v0.4.4** is the latest GitHub *release*. A newer tag `v0.4.5-1`
  exists without a release; not used.
- **Launcher 4.0** is the latest release. `master` is 5 commits ahead
  (README edit, patch progress display, formatting, removal of a mirrors
  parameter, 2026-09-10..13). Revisit in Phase 2 when the contract tests are
  written: the progress display change touches the `tqdm` path the adapter
  replaces.
- The launcher pin is also recorded in `third_party/launcher.pin`; the guard
  rails fail if the gitlink, the pin file or the checked-out tree disagree.

## Devkit packages (installed in `docker/ounce-devkit`)

Installed from GitHub release assets, SHA-256 checked (ADR 0002).

| Package | Release | SHA-256 of `.pkg.tar.zst` | Source commit | Licence |
|---|---|---|---|---|
| libounce | ouncebrew/libounce 20261117.1 | `74336b088305dabb4c12a6060cb7fbf38936e137a0f2b2abc86413b561264810` | `7270a6acee972acf628c482e577b53c7e6f02e76` | ISC (`LICENSE.md`, `LICENSES/`) |
| ouncevk | ouncebrew/ouncevk 20261117.1 | `061dd6a172255e272c5258578745533db043aff05e8b321d8a86850fd702ffeb` | `06d7dbdf8346325a171c117bf29414724f10a8b2` | MIT + others (Mesa, `licenses/`) |
| libkaihen | ouncebrew/kaihen 20261117.1 | `9b53139a92ca8b7b1d3c4249a5f7a0987f089f7a9b74e6193889eef9df820606` | `3695f364f9270686aa72cc39627bb1281752b2d3` | ISC (`libkaihen/LICENSE`); rest of kaiHEN GPL-2.0 |

The same hashes are in `docker/ounce-devkit/Dockerfile`. These are the releases
listed in ouncebrew/pacman `sources` at `6f73dae534b91d16458ef1b8c60c86505824572e`
(2026-11-17), i.e. what `[ounce]` served on 2026-11-24. Note: the `20261117.1`
tags are annotated; `git ls-remote` shows tag-object ids (`c9c9217…`,
`ac78e56…`, `28a6785…`), the commits above are what they point to.

Newer upstream tags exist and are **not** used yet: ouncevk 20261118,
20261120, 20261123; kaiHEN 20261117b. Bump deliberately, with a re-probe
(Phase 1), never implicitly.

## Base images

| Image | Digest (multi-arch index) | Platforms | Used by |
|---|---|---|---|
| `devkitpro/devkita64:20260219` | `sha256:1fc388c3a0d34bd2045a6dadcb1020e069d5f876a187fd705de14b4440c00282` | linux/amd64, linux/arm64 | ounce-devkit |
| `debian:12` | `sha256:1d04200c2ece1d4d75a2a6f8e11ebce7d86a2ae28b34bb2c9cbb3ee9f4953e75` | amd64, arm64/v8, … | bench-arm64 (arm64), ref-amd64 (amd64) |

Debian packages come from `snapshot.debian.org` at `20261120T000000Z`.
The devkitA64 image already contains devkitA64 r29.2-1, devkita64-cmake
1.1.3-1, switch-cmake 1.5.2-1, switch-tools 1.13.1-1, dkp-toolchain-vars
1.0.5-1, switch-zlib 1.3.1-1 and libnx 4.12.0-1 (checked with `dkp-pacman -Q`
in the container on 2026-11-24), so libounce's dependencies are satisfied
without touching devkitPro's rolling repositories.

## Reference clones (`third_party/reference/`, gitignored, `make reference`)

| Name | Upstream | Commit | Date | Licence |
|---|---|---|---|---|
| ounce-devkit | ouncebrew/ounce-devkit (main) | `5e957599bd498643d82e5470aec80da67a12685d` | 2026-11-17 | MIT |
| ounce-pacman | ouncebrew/pacman (main) | `6f73dae534b91d16458ef1b8c60c86505824572e` | 2026-11-17 | MIT |
| kaihen | ouncebrew/kaihen 20261117.1 | `3695f364f9270686aa72cc39627bb1281752b2d3` | 2026-11-17 | GPL-2.0-only; `libkaihen/` ISC |
| libounce | ouncebrew/libounce 20261117.1 | `7270a6acee972acf628c482e577b53c7e6f02e76` | 2026-11-17 | ISC |
| ounce-examples | ouncebrew/ounce-examples (main) | `3856a475f0f31e58241cec8985a12838e746d96d` | 2026-11-19 | public domain mark (README) |
| ouncevk (FULL=1) | ouncebrew/ouncevk 20261117.1 | `06d7dbdf8346325a171c117bf29414724f10a8b2` | 2026-11-17 | MIT + others |

## CI tools

| Tool | Version | Pin |
|---|---|---|
| actions/checkout | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| actions/setup-python | v7.1.0 | `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` |
| actions/upload-artifact | v7.0.2 | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` |
| gitleaks linux x64 | 8.30.1 | tarball SHA-256 `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb` |

## What was relied on, per phase

### Phase 0 (2026-11-24)

- ounce-devkit `Dockerfile` and `install.sh` at `5e95759`: base image
  `devkitpro/devkita64:20260219`; the packages `libounce ouncevk libkaihen`;
  the `[ounce]` signing key fingerprint `DFEAE7FA965D1E6C0D41D4D75DB9FDBFA4A4DE29`
  (not used by our Dockerfile, which checks SHA-256 instead). `install.sh`
  also installs `glslang-tools` via apt; we omit it until Vulkan shaders are
  needed (Phase 6).
- ounce-devkit `README.md`: libnx Makefiles switch to
  `include $(DEVKITPRO)/libounce/switch2_rules`; `-lnx` links libounce.
- ouncebrew/pacman `README.md` and `sources` at `6f73dae`: `[ounce]` serves
  exactly one release per package; packages are attached to each library's
  GitHub release.
- ounce-examples `templates/application/Makefile` and
  `graphics/printing/hello-world/source/main.c` at `3856a47`: the libounce
  console API (`consoleInit`, `padConfigureInput`, `padInitializeDefault`,
  `padUpdate`, `padGetButtonsDown`, `appletMainLoop`, `consoleUpdate`,
  `consoleExit`) and `ARCH := $(SWITCH2_CPU) -mtp=soft -fPIE`. The hello
  program built with these, unchanged, under `-Werror`.
