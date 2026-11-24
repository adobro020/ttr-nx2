# TTR NX2 — prompt pack for Claude Code

Prompts for Claude Opus 5.5 in Claude Code to build an unofficial Toontown
Rewritten client for Nintendo Switch 2 under kaiHEN: the original x86-64
`TTREngine` through Box64, the Simple TTR Launcher's Python source on ARM64
Linux Python 3.12, and a native graphical login.

Researched and written 2026-11-24.

## What is here

| File | Use |
|---|---|
| `CLAUDE.md` | The master prompt. Claude Code loads it automatically in every session started in this folder. |
| `docs/ARCHITECTURE.md` | Research findings, platform constraints, the chosen architecture, feasibility gates, sources. |
| `prompts/phase-00-workspace-and-repo.md` | Mac setup, containers, pinned upstreams, GitHub project, CI guard rails. |
| `prompts/phase-01-hardware-probes.md` | Deploy and log loop; a probe NRO that measures the console's real limits. Gate G3. |
| `prompts/phase-02-reference-baselines.md` | Launcher contract tests; engine reconnaissance on ordinary Linux. Gates G1, G2. |
| `prompts/phase-03-gx-runtime.md` | The in-process Linux runtime (LKL + gx), `execve`, hostcall bridge. |
| `prompts/phase-04-python-guest.md` | CPython 3.12 with `cryptography` and friends as a guest. Gate G4. |
| `prompts/phase-05-launcher-adapter.md` | Driving the unmodified launcher through a protocol. |
| `prompts/phase-06-native-login-ui.md` | The graphical login interface. |
| `prompts/phase-07-box64-interpreter.md` | Box64 as a guest, interpreter only. Gate G5. |
| `prompts/phase-08-display-audio-input.md` | X11, OpenGL, audio and control shims. |
| `prompts/phase-09-first-boot.md` | First end-to-end boot of the game. |
| `prompts/phase-10-staged-jit-dynarec.md` | Box64's recompiler on kaiHEN's JIT model. Gate G6. |
| `prompts/phase-11-playable.md` | Performance, stability, controls. Gate G7. |
| `prompts/phase-12-release.md` | Packaging, licences, security, documentation. Gate G8. |

## How to use it

1. Make this folder the root of the new project (rename it `ttr-nx2` and run
   `git init`), or copy its contents into an empty repository.
2. Start Claude Code there with Opus 5.5:

   ```bash
   claude --model claude-opus-5-5
   ```

3. Begin each phase in a **new session** with:

   > Run Phase N. Follow `prompts/phase-NN-….md`. Start by reading
   > `CLAUDE.md`, `docs/ARCHITECTURE.md` and `docs/STATUS.md`.

4. When a phase asks for the console, follow the checklist it wrote in
   `docs/hardware/`, then give the logs back in the same or a new session.
5. A phase is done when every acceptance criterion has evidence beside it.
   Items that need the console stay "pending human" until the logs exist.

## Order and dependencies

```
0 ─┬─ 1 (hardware probes, G3) ──────────────┐
   └─ 2 (baselines, G1 G2) ─┐               │
                            ├─ 3 (runtime) ─┼─ 4 (Python, G4) ─ 5 (adapter) ─ 6 (GUI) ─┐
                            │               └─ 7 (Box64 interp, G5) ─ 8 (shims) ───────┼─ 9 (first boot)
                            │                                                          │
                            └──────────────────────────────────────────────────────────┴─ 10 (JIT, G6) ─ 11 (G7) ─ 12 (G8)
```

Do Phase 2 early. Gate G1 (whether the engine binary can be loaded at a high
address) can end the project and takes an afternoon to check.

## The architecture in brief

One homebrew process. Native code (libounce, OunceVK, libkaihen) provides the
login UI and platform services. The Linux kernel built as a library (LKL)
plus the `gx` guest executor from Chromium NX run unmodified aarch64 Linux
programs inside that process: first CPython 3.12 with the launcher, then
Box64, which runs `TTREngine`. Box64's recompiler has to be ported to
kaiHEN's JIT, which writes code to a staging buffer and publishes it to a
separate execute-only mapping.

## Read this before starting

- **This is a research project with real chances of stopping early.** The
  gates are honest decision points, not formalities. The two largest unknowns
  are whether the engine binary is position-independent (G1) and whether
  Box64's recompiler can be made fast under kaiHEN's JIT rules (G6).
- **The Switch 2 homebrew stack is days old.** kaiHEN's first public release
  was around 2026-11-13. Limits and APIs described here may change; the
  prompts tell Claude to re-read the pinned sources and to measure on the
  console rather than trust this document.
- **Your console and account are at risk.** kaiHEN's authors warn that
  homebrew can brick a console. A modified console may lose Nintendo's online
  services. TTR may not permit or support playing this way; ask them before
  publishing anything (G8). The prompts keep the repository private until you
  decide.
- **Credentials stay with you.** The prompts forbid Claude from handling your
  TTR login. Automated tests use a local fake of the login API.
- **No game files are distributed.** The launcher downloads them on the
  device from TTR's servers, as it does on a PC.

## Sources

See section 7 of `docs/ARCHITECTURE.md`.
