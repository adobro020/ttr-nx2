# TTR NX2 (unofficial)

An **unofficial** homebrew application, in development, that aims to play
Toontown Rewritten on a Nintendo Switch 2 running kaiHEN. It runs the
unmodified Simple TTR Launcher on ARM64 Linux Python inside the homebrew
process, and starts the original Linux x86-64 game engine through Box64. It
does not boot Linux and does not touch the console's kernel.

**This project is not affiliated with, endorsed by or supported by Nintendo,
Disney or the Toontown Rewritten team.** All names are used only to describe
what the software works with.

**This repository contains no game files and never will.** The launcher
downloads the game on your own console from Toontown Rewritten's servers,
just as it does on a PC. CI refuses any commit that adds game files.

## Status

Early research. Nothing here plays the game yet, and the project may stop at
a feasibility gate. See [`docs/STATUS.md`](docs/STATUS.md) for the gates and
phase progress and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the
design.

## Risks you accept by using homebrew

- kaiHEN's authors warn that homebrew has full system access and can brick a
  console. This project only reads and writes under `sdmc:/switch/ttr-nx2/`.
- A console used for homebrew may lose access to Nintendo's online services.
- Do not update your console's firmware without checking which versions
  kaiHEN supports.
- Toontown Rewritten may not support or permit playing this way.

## Building

On an Apple-silicon Mac, follow [`docs/dev-setup-macos.md`](docs/dev-setup-macos.md), then:

```bash
git clone --recurse-submodules <this repository>
cd ttr-nx2
make doctor
make hello
```

Every console and guest build runs in a container under `docker/`.

## Licence

GPL-2.0-only (see `LICENSE`), because it incorporates GPL-2.0 code from
Chromium NX's gx and from LKL. Third-party components and their licences are
listed in [`THIRD_PARTY.md`](THIRD_PARTY.md).

The phase prompts used to develop this project are in [`prompts/`](prompts/).
