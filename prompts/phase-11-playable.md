# Phase 11 — Performance, stability and controls: make it playable

Read `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/STATUS.md` and
`docs/perf/` first. Depends on Phase 10. Decides gate **G7**.

## Goal

A person can play a normal session on the console, handheld or docked, at
the targets below, for two hours, without needing a keyboard.

## Targets

Agree these with the human at the start of the phase and write them into
`docs/STATUS.md`; the defaults are:

| Measure | Target |
|---|---|
| Average frame rate, quiet playground, 720p | ≥ 30 fps |
| Average frame rate, busy playground or street | ≥ 24 fps |
| Battle, trolley game, fishing | ≥ 24 fps |
| 99th-percentile frame time | ≤ 100 ms |
| Start of app to login screen | ≤ 15 s |
| Handoff to first game frame (warm) | ≤ 90 s |
| Audio underruns per hour | 0 |
| Memory headroom at peak | ≥ 15% of the Phase 1 budget |
| Soak without the process ending | 2 hours |

If a target cannot be met, say so with numbers; do not redefine it quietly.

## Work

1. **Instrumentation** (off by default, enabled from settings): a frame-time
   histogram, time spent per layer per frame (emulated code, GL hostcalls,
   driver, audio, syscalls, JIT publish), translation statistics, memory
   over time. Output to the log and to an on-screen overlay.
2. **Benchmark scenes**: a written procedure the human can repeat (which
   playground, where to stand, how long) so numbers are comparable between
   builds. Results go in `docs/perf/scenes.md` with the commit hash.
3. **Optimise in order of measured cost.** Likely candidates, each to be
   confirmed by the instrumentation before work starts: GL call forwarding
   overhead and redundant state changes; shader compilation stutter (a
   persistent cache if the driver supports one); JIT publish batching and
   warm-up (translation cache from Phase 10 if viable); thread placement on
   the cores Phase 1 found usable; Box64 settings per `USAGE.md`; syscall
   trampoline cost for hot calls; SD card I/O during area loads; resolution
   and swap interval.
4. **Stability**: a two-hour soak with memory tracking (no upward slope in
   committed guest memory, records or mappings); repeated area transitions;
   sleep and wake mid-session (the connection will drop; the outcome must be
   the game's own disconnect dialog or a clean return, never a hang); dock
   and undock; Wi-Fi loss and return.
5. **Controls**: refine the default profile with the human's feedback;
   on-screen button hints overlay (toggle); pointer speed and dead zones;
   chat through the software keyboard; a profile editor screen in the
   launcher UI or documented JSON; USB keyboard and mouse pass straight
   through.
6. **Settings in the launcher UI**: resolution, frame cap, interpreter or
   recompiler, instrumentation, control profile.
7. **User-facing failure handling**: the last-session record from Phase 9
   drives a "the game closed unexpectedly" screen that offers to write a
   redacted report bundle to the SD card for a GitHub issue.
8. **Play-test checklist** for the human
   (`docs/hardware/phase-11-playtest.md`): tutorial or existing toon, moving
   between playground and street, a battle, a trolley game, fishing, the
   estate, the book and its pages, SpeedChat, typed chat, friends list,
   changing district, logging out. Each with pass, fail, or notes.

## Deliverables

Instrumentation, scene procedure and results, optimisation PRs each with
before-and-after numbers, soak results, final control profile, settings
screens, failure-report flow, play-test results.

## Acceptance criteria

- [ ] Every optimisation PR quotes before and after numbers from the same
      scene and the same console mode.
- [ ] `docs/perf/scenes.md` has a final table against every target above,
      measured on the console by the human, handheld and docked.
- [ ] Soak: two hours, logs show no growth trend in committed memory,
      memory records or JIT mappings (first versus last 15 minutes within 3%).
- [ ] Sleep and wake, dock and undock, and Wi-Fi loss each end in a defined,
      documented outcome, tested on the console.
- [ ] The play-test checklist is filled in by the human; every "fail" has an
      issue.
- [ ] The report bundle produced after a forced kill contains no credential
      or cookie (automated scan) and is under 1 MB.
- [ ] All earlier suites still pass in CI.
- [ ] G7 is marked in `docs/STATUS.md`, with the list of targets met and not
      met.

## Hardware

Several sessions; plan them with the human. Benchmarks are run after the
console has been on for ten minutes, so thermal state is comparable.

## If blocked

- The bottleneck is the GPU driver: reduce resolution, report upstream with
  a native reproducer, and consider the low-level graphics API
  (`drako3d`) only with the human's agreement, since it is a large change.
- The bottleneck is emulated code in one hot area: profile which x86-64
  functions dominate and look for a missing recompiler path, not for a
  game-specific hack.
