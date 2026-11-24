# Phase 0 — Mac workspace, toolchain and repository

Read `CLAUDE.md` and `docs/ARCHITECTURE.md` first.

## Goal

A fresh clone on this Mac can build a Switch 2 "hello" NRO and run an empty
test suite with one command each, and the GitHub project is set up to carry
the remaining phases.

## Why first

Every later phase assumes reproducible container builds, pinned upstreams and
a CI that refuses secrets and game files. Getting this wrong later is costly.

## Work

1. **Inspect the Mac.** Record `uname -m`, macOS version, free disk space
   (plan for 40 GB), and which of these exist: Xcode command line tools,
   Homebrew, `git`, `gh`, Docker Desktop or OrbStack, Python 3.12, `lftp`,
   `jq`, `shellcheck`, `cmake`. Install what is missing with Homebrew after
   listing it for the human. If the Mac is Intel, note that arm64 containers
   will be emulated and slow, and say so in `docs/STATUS.md`.
2. **Create the repository skeleton** exactly as laid out in `CLAUDE.md`,
   with `LICENSE` (GPL-2.0-only), `THIRD_PARTY.md`, a `README.md` that states
   what the project is, that it is unofficial and unaffiliated, and that it
   ships no game files. Add `.gitignore` entries for game files, `*.ext4`,
   `launcher.json`, `logs/`, `cache/`, `ref/`, build output.
3. **Pin the upstreams as submodules** under `third_party/`:
   `shodowlo/chromium-nx`, `ptitSeb/box64` (latest release tag),
   `mike406/Simple-TTR-Launcher`. Clone `ouncebrew/ounce-devkit`,
   `ouncebrew/kaihen` and `ouncebrew/libounce` for reference reading at the
   versions the devkit packages provide. Write every commit hash, licence and
   date into `docs/upstream-notes.md`.
4. **Containers.** Write `docker/ounce-devkit/` (follow ounce-devkit's own
   Dockerfile and README; check which CPU architectures the
   `devkitpro/devkita64` base image supports and set `--platform`
   accordingly), `docker/bench-arm64/` (Debian 12 arm64 with a C toolchain,
   `flex`, `bison`, `bc`, `libelf-dev`, `cmake`, `python3`, `e2fsprogs`) and
   `docker/ref-amd64/` (Debian 12 x86-64 with a C toolchain and `binutils`).
   Pin base images by digest.
5. **`Makefile` front end** with the targets named in `CLAUDE.md`. `make
   doctor` prints one line per requirement with pass or fail and exits
   non-zero on any failure. Targets that do not exist yet print "not
   implemented in this phase" and fail.
6. **Prove the toolchain.** Build one program from `ouncebrew/ounce-examples`
   (or a ten-line libounce console program) inside the devkit container as
   `build/hello.nro`. Optionally also install devkitPro pacman natively and
   the devkit with `sh install.sh`, but the container is the build of record.
7. **Guard rails.** A pre-commit hook and a CI job that fail when: a file
   over 5 MB is added; a path matches known game file patterns (`TTREngine*`,
   `phase_*.mf`, `*.mf`); the launcher submodule differs from its pinned
   commit; a secret scanner (gitleaks) or a pattern for
   `TTR_PLAYCOOKIE=<value>` matches.
8. **GitHub.** Ask the human before each of these. Create a **private**
   repository with `gh`. Add labels and one milestone per phase as described
   in `CLAUDE.md`, an issue template (bug, hardware report), a PR template
   containing an acceptance checklist section, and branch protection on
   `main` requiring CI. Add the first workflow: lint, `make doctor` (CI
   variant), build `hello.nro` in the devkit container, upload it as an
   artifact. Use an arm64 Linux runner for bench jobs when they arrive.
9. **Project records.** `docs/STATUS.md` with the gate table G1–G8 (all
   "open"), a phase table, and an "open questions" list.
   `docs/adr/0001-architecture.md` summarising the chosen architecture and
   pointing at the architecture document.

## Deliverables

Repository skeleton, three container definitions, `Makefile`, `hello.nro`
built in CI, guard-rail checks, GitHub project configuration, `STATUS.md`,
first ADR, `docs/dev-setup-macos.md` (the exact steps you performed, so a
second Mac can be set up by following it).

## Acceptance criteria

- [ ] `make doctor` exits 0 on this Mac and its output is pasted in the PR.
- [ ] `git clone --recurse-submodules` into a new directory followed by
      `make hello` produces `build/hello.nro` with no manual steps. The file
      has the `NRO0` magic at offset 0x10 (show the `xxd` line).
- [ ] The same build passes in GitHub Actions; link the run.
- [ ] Committing a dummy file named `TTREngine` is rejected by the hook and
      by CI (demonstrate on a throwaway branch, then delete it).
- [ ] Committing a line `TTR_PLAYCOOKIE=abc123` is rejected the same way.
- [ ] `docs/upstream-notes.md` lists a commit hash and licence for every
      upstream, and `git submodule status` matches it.
- [ ] `docs/dev-setup-macos.md` exists and names every installed tool and
      version.
- [ ] The repository is private (show `gh repo view --json visibility`).

## Hardware

Optional smoke test for the human: copy `hello.nro` to the SD card and start
it from hbmenu. Phase 1 does this properly.

## If blocked

- devkit container does not build on this Mac's architecture: build it for
  `linux/amd64` under emulation and record the build time.
- The `[ounce]` package repository is unreachable: build libounce, OunceVK
  and libkaihen from source at pinned commits inside the container.
