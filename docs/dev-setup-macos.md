# Developer setup on macOS

The exact steps performed on the first development Mac on 2026-11-24, so a
second Mac can be set up the same way. `make doctor` checks the result.

## The Mac it was done on

| Item | Value |
|---|---|
| CPU | arm64 (Apple silicon) — arm64 containers run natively |
| macOS | 27.2.1 (build 26B131) |
| Free disk | 15–17 GB at setup time (40 GB planned; see `docs/STATUS.md`) |

On an Intel Mac everything works, but the arm64 bench containers run under
QEMU emulation and are many times slower.

## 1. Already present before Phase 0

| Tool | Version | Source |
|---|---|---|
| Xcode command line tools | `/Library/Developer/CommandLineTools` | `xcode-select --install` |
| Homebrew | 7.0.14 (7.0.16 after auto-update) | https://brew.sh |
| git | 2.54.0 (Apple Git-157) | Xcode CLT |
| jq | 1.7.1-apple | macOS |
| xxd | macOS | macOS |
| Docker CLI | 29.10.0 | Homebrew `docker` |
| Colima | 0.10.3 | Homebrew `colima` |

If any is missing on a new Mac:

```bash
xcode-select --install
```

```bash
brew install docker colima jq
```

## 2. Installed in Phase 0

```bash
brew install gh python@3.12 lftp shellcheck cmake gitleaks docker-buildx
```

| Tool | Version installed |
|---|---|
| gh | 2.105.0 |
| Python | 3.12.16 (`python3.12`; the system `python3` is 3.13 and is only used by the git hook) |
| lftp | 4.9.3 |
| shellcheck | 0.11.0 |
| cmake | 4.5.1 |
| gitleaks | 8.30.1 |
| docker-buildx | 0.39.1 |

## 3. Docker CLI plugin path

Homebrew's buildx is a CLI plugin that Docker only finds when told where it
is. `~/.docker/config.json` gained one key (a backup of the original was left
at `~/.docker/config.json.bak-ttrnx2`):

```json
"cliPluginsExtraDirs": ["/opt/homebrew/lib/docker/cli-plugins"]
```

Check with `docker buildx version`.

## 4. Container runtime (Colima)

Colima's VM must (a) use Apple's Virtualization framework with Rosetta, so
the x86-64 reference container is fast, and (b) share this project folder.
A folder that is not shared appears **empty** inside containers and builds
fail with "no makefile found".

On this Mac Colima's mounts were restricted to one other folder, so the
project folder was added to `~/.colima/default/colima.yaml` (backup at
`~/.colima/default/colima.yaml.bak-ttrnx2`):

```yaml
vmType: vz
mountType: virtiofs
mounts:
  # ...any mounts you already had stay as they are...
  - location: /Users/<you>/Downloads/ttr-nx2   # added
    writable: true
```

Then:

```bash
colima start --vz-rosetta
```

(`colima restart` after editing the mounts.) The VM has 6 CPUs, 6 GiB memory
and a 24 GiB disk. Docker Desktop or OrbStack work too; make sure the project
folder is in their file-sharing list. `make doctor` checks it
(`docker-mount`).

## 5. Clone and check

```bash
git clone --recurse-submodules <repository URL> ttr-nx2
cd ttr-nx2
make hooks
make doctor
```

`make hooks` sets `core.hooksPath=.githooks`, which enables the guard-rail
pre-commit hook. If you cloned without `--recurse-submodules`:

```bash
git submodule update --init
```

## 6. Build and test

```bash
make hello
make test
make lint
make guardrails
make images
```

- `make hello` builds the devkit container on first use (about 1 minute plus
  the base image pull) and writes `build/hello.nro`; it prints the `NRO0`
  line.
- `make images` also builds `bench-arm64` (~1 minute, ~1 GB) and
  `ref-amd64` (~1 minute under Rosetta, ~0.7 GB).
- `make reference` clones the read-only upstream sources (kaiHEN, libounce,
  ounce-devkit, ounce-examples, ouncebrew/pacman) into
  `third_party/reference/`. Add `FULL=1` for OunceVK (~500 MB).

## 7. GitHub CLI

```bash
gh auth login
```

Done by the human; Claude does not handle account credentials. Repository
creation and configuration are in `tools/github/setup-project.sh` and run
only with the human's approval.
