# 0005 — Reference runs of TTREngine: stock Box64, offline, placeholder cookie

Date: 2026-11-24. Status: accepted (Phase 2).

## Context

Gate G2 and the dependency list for Phases 7–9 need TTREngine running under
stock Box64 on arm64 Linux, instrumented. Without `TTR_PLAYCOOKIE` the engine
prints a message and exits at once, so no window, GL or audio is exercised.
A real login is the human's to perform (CLAUDE.md "Who does what"), and
automated contact with TTR's servers is not allowed (rule 5).

## Options

1. Wait for the human's logged-in run for everything.
2. Run with network on and a dummy cookie against TTR's game server.
   Contacts TTR's servers with a bogus credential: rejected (rule 5).
3. Run in a container with `--network none`, `TTR_GAMESERVER` set to a closed
   loopback port and a placeholder cookie value. The engine starts, opens
   its window, initialises GL and audio, and stops at the title screen
   waiting for a key press before it connects.

## Decision

Option 3 for everything that does not need a game session
(`make recon-run`, `tools/ref/run-engine.sh`), plus a run sheet and helper
(`make human-run`, `docs/recon/human-run.md`) for the human to reach the
toon selection screen with their own account. The game directory is copied
into the container per run so `ref/game` stays as the patcher left it;
Box64 is installed to a staging directory and pointed at with
`BOX64_RCFILE`/`BOX64_LD_LIBRARY_PATH`. Software GL is Mesa llvmpipe on Xvfb;
audio is ALSA's null device.

## Consequences

- G2 can be decided "pending human run" without any credential handling.
- Numbers from the title screen are a baseline for later phases, not the
  in-game load; anything that needs a session is marked pending.
- Recon documents are named `docs/recon/engine-<sha1 prefix>.md`, not
  `ttrengine-<version>.md` as the phase prompt says: the guard rails reject
  any file whose name starts with `ttrengine` (ADR 0003), and weakening that
  check for documentation is not worth the risk.
- Screenshots and traces stay under `build/` (git-ignored): they show the
  game's own art (rule 8).
