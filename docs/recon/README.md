# docs/recon/

Facts about the TTR Linux client and the launcher, gathered on ordinary Linux
(Phase 2). No binaries, no game data, no disassembly listings, no screenshots
in this folder; command output is quoted only as far as it states a fact.

| File | What |
|---|---|
| `launcher-contract.md` | Simple TTR Launcher 4.0: every terminal I/O call site, settings schema, files written, network calls, the game launch. Spec for Phase 5. |
| `engine-91bff107.md` | TTREngine (Linux build `ttr-live-v4.4.5h`, SHA-1 `91bff107…`): ELF facts (G1), behaviour under stock Box64 on arm64 (G2), the dependency list for Phases 7–9. |
| `engine-91bff107-imports.txt` | Imported symbol names of TTREngine and the bundled `libopenal.so.1`, by providing library. |
| `human-run.md` | Run sheet for the human's logged-in reference run. |

Engine documents are named `engine-<SHA-1 prefix>.md`, not
`ttrengine-<version>.md`: the guard rails reject every file whose name starts
with `ttrengine` (ADR 0005).

Reproduce: `make fetch-game` (asks TTR's CDN; see the tool's docstring),
`make recon-static`, `make box64-bench`, `make recon-run RUN=… FAKE_SERVER=1 …`
(raw output in `build/recon/` and `build/recon-run/`, git-ignored).
