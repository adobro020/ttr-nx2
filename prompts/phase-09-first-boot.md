# Phase 9 — First boot of TTREngine, end to end (interpreter)

Read `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/STATUS.md` and the Phase 2
recon first. Depends on Phases 5, 6, 7 and 8, and on G1 and G2 having passed.

## Goal

On the console: graphical login with a real account, download of the game to
the SD card, handoff, and the original `TTREngine` running under the Box64
interpreter far enough to choose a toon and stand in a playground. It will be
very slow. This phase is about correctness.

## Ground rules for this phase

- Real logins are done by the human, on the console or in the bench
  container on their own machine. You never see the credentials or the
  cookie, and you prepare the tooling so that logs cannot contain them.
- One login per test session is plenty. No scripted or repeated logins
  against the real service.
- The engine and its files are used as downloaded. No edits.

## Work

1. **Integrate**: the release-configuration rootfs gains Box64, the x86-64
   support libraries, the shims, and the engine's `box64rc` profile
   (interpreter). The adapter's exec target becomes Box64 with the engine
   path. Engine output goes to the log only when the user enables "game log",
   and always through the redaction filter.
2. **Install directory behaviour**: confirm on the bench what the engine
   reads and writes beside itself (settings, logs, caches, screenshots),
   whether it needs execute permission bits or case-sensitive names, and
   that all of it works on the SD card's filesystem through hostfs. Fix in
   the runtime's filesystem layer if not.
3. **Bench rehearsal first**: write `docs/hardware/phase-09-bench-run.md` so
   the human can run the full flow inside the bench container in nx2-like
   mode with the host display forwarded (login in the Mac mock GUI, download,
   handoff, engine through our Box64 build and shims). Work through every
   missing syscall, unimplemented shim symbol, GL error and audio problem
   here, where failures are visible. Each fix lands with a small test added
   to the suites from Phases 3, 7 and 8.
4. **Engine life cycle**: quitting from the game's own menu ends the process
   cleanly and returns to the HOME menu; HOME and sleep are survived or end
   in a clean exit with a message on next start; a lost connection shows the
   game's own dialog; a start with too little free space is refused by the
   launcher UI before download.
5. **Diagnostics for a silent death**: a "last session" record written at
   each major stage (login done, patch done, handoff, engine window created,
   first frame, first network packet) so the next start can tell the user how
   far the previous run got and offer to save a redacted report.
6. **Measure**: time from handoff to the first frame, frames per second at
   toon selection and in a playground, peak memory (guest, kernel library,
   host), memory records, JIT mappings. Record them in `docs/perf/engine.md`
   as the interpreter baseline.
7. **Cookie test**: on the bench, run the engine handoff with a known fake
   cookie against a stub game server address and assert that the cookie
   string appears in no file under `logs/`, `data/` or `cache/`, and in no
   line sent to the log server.

## Deliverables

Integrated build, bench run sheet, life-cycle handling, last-session record,
measurements, new regression tests, `docs/hardware/phase-09-checklist.md`.

## Acceptance criteria

- [ ] Bench, nx2-like mode, human-run with a real account: the toon
      selection screen is reached (screenshot in `docs/hardware/`), then a
      playground. The run's log has no "unimplemented symbol" and no "unknown
      syscall" lines.
- [ ] Every problem found during rehearsal has a regression test that fails
      without its fix (listed in the PR).
- [ ] The cookie test passes in CI.
- [ ] Hardware (pending human until logged), human-run with a real account:
  - [ ] login, token prompt if the account uses one, and download complete
        from the graphical UI;
  - [ ] the engine's window appears, toon selection is reached, a playground
        loads, and the toon can be moved with the controller (photos);
  - [ ] sound is audible;
  - [ ] fifteen minutes in the playground without the process ending;
  - [ ] quitting from the game returns to the HOME menu;
  - [ ] logs pulled afterwards contain no credential or cookie (the human
        runs `tools/scan-logs.sh` before sharing them).
- [ ] Peak memory and record counts are under the Phase 1 budgets with the
      margins written down.
- [ ] `docs/STATUS.md` records the interpreter-mode frame rates.

## Hardware

Two sessions: first boot (expect long loading under the interpreter; the
checklist says how long to wait before calling it a hang), and the life-cycle
checks.

## If blocked

- The engine dies silently on the console but runs on the bench: use the
  last-session record to find the stage, then tighten nx2-like mode until
  the bench reproduces it.
- The engine refuses to start for a reason that looks like an integrity or
  environment check: stop. Do not bypass it. Report to the human; this is a
  question for the TTR team (gate G8).
- Loading under the interpreter takes impractically long to test: move on to
  Phase 10 and come back to finish this phase's hardware items with the
  recompiler.
