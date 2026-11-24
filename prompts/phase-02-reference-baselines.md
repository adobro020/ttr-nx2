# Phase 2 — Reference baselines off the console

Read `CLAUDE.md`, `docs/ARCHITECTURE.md` and `docs/STATUS.md` first.
Depends on Phase 0. Independent of Phase 1. Decides gates **G1** and **G2**.

## Goal

Know exactly what the launcher and the engine need, by running both on
ordinary Linux, before any of it meets the console.

## Why now

G1 (can the engine be loaded at a high address?) can end the project and
costs an afternoon to check. G2 (does it run under stock Box64 on ARM64
Linux?) is the baseline every later failure is compared against.

## Work

### A. Launcher contract

1. Build `tools/fake_ttr_api/`: a local HTTPS server that implements the
   login API as documented in `ToontownRewritten/api-doc` `login.md` and as
   the pinned launcher calls it: failure with banner, partial (token) with a
   second partial, delayed (queue) with decreasing position, success; the
   mirrors endpoint; a patch manifest; bz2-compressed files and bsdiff patches
   generated from small fixture files. Scenarios are selectable per test.
2. Write a pytest suite that runs the **unmodified** launcher modules on
   macOS Python 3.12 against the fake server, with requests redirected to it
   at the transport layer and terminal I/O scripted. Cover: each login
   outcome; stored accounts with keyring off and master-password encryption
   on (Argon2id and Fernet round trip); fresh install; incremental bsdiff
   update; hash mismatch; network failure with retries; the environment and
   arguments passed to the process launch.
3. Write `docs/recon/launcher-contract.md`: every terminal I/O call site in
   the pinned source (function, line, prompt text, expected answer type), the
   settings schema, the files it writes, and the exact launch call. This is
   the specification for Phase 5.

### B. Engine files

4. `tools/fetch_game_files.py`: in a Linux container, call the upstream
   `patcher.Patcher().check_update(<dir>, <manifest path>)` to download the
   Linux files into `ref/game/` (git-ignored). This uses the launcher's own
   patcher and public CDN and needs no login. Ask the human before the first
   run (it downloads a few gigabytes from TTR's servers) and run it once.

### C. Static reconnaissance (in `docker/ref-amd64`)

5. For `TTREngine` and every shared object shipped beside it, record in
   `docs/recon/ttrengine-<version>.md`: ELF type (`ET_DYN` or `ET_EXEC`),
   program headers and load addresses, `DT_NEEDED`, undefined dynamic symbols
   grouped by providing library, TLS model, stack flags, section sizes.
   Record facts only: no disassembly listings, no copies of the binary.
6. **Decide G1**: PIE or not; any sign of low-address dependence
   (`MAP_32BIT`, non-PIC relocations, a fixed base).

### D. Dynamic reconnaissance (in `docker/bench-arm64`, stock Box64)

7. Build stock Box64 at the pinned tag for generic ARM64. Add Xvfb, Mesa
   (software rendering) and a null or file audio device.
8. Run `TTREngine` under Box64 without credentials and record how far it
   gets. Then prepare `docs/recon/human-run.md`: steps for the human to run
   the upstream launcher in this container with their own account so the
   engine reaches the toon selection screen, and which logs to keep (with a
   reminder to delete anything containing the cookie).
9. From those runs collect: libraries loaded and which Box64 wrapped versus
   emulated (`BOX64_LOG`); the syscall set (`strace -f -c` on the Box64
   process); signals for which handlers are installed and any actually
   delivered; `mmap` flags and whether executable anonymous memory is created
   at run time (thunks, closures); thread count; peak resident memory; the GL
   context requested, GL version and extensions actually used (apitrace or
   Mesa debug output); the X11 and GLX entry points called; the audio library
   and device parameters; files written in the install directory.
10. Run once with `BOX64_DYNAREC=0` and record CPU time per frame at the same
    screen, as the interpreter baseline.
11. **Decide G2** and write the dependency list that Phases 7–9 must satisfy:
    syscalls gx must support, symbols the shims must export, GL features
    required, signals whose absence matters.

## Deliverables

Fake API server, launcher contract tests, `launcher-contract.md`, fetch tool,
`ttrengine-<version>.md`, human run sheet, G1 and G2 verdicts.

## Acceptance criteria

- [ ] `make test` runs the launcher contract suite on macOS: all scenarios
      listed in step 2 pass; show the summary line.
- [ ] `git status` in `third_party/Simple-TTR-Launcher` is clean after the
      test run.
- [ ] `launcher-contract.md` lists every `input`, `pwinput`, `print`-prompt,
      `confirm`, `clear`, `webbrowser`, `tqdm` and `subprocess` call site
      with file and line at the pinned commit.
- [ ] The recon document answers, with command output quoted: ELF type; load
      addresses; needed libraries; imported symbol counts per library.
- [ ] G1 has a verdict with the `readelf -h` and `readelf -l` lines beside it.
- [ ] Syscall list, signal list, GL requirements and audio parameters are
      recorded from a run that reached at least the engine's own window
      creation; items that need the human's logged-in run are marked pending.
- [ ] G2 has a verdict, or is "pending human run" with the run sheet ready.
- [ ] CI's game-file check passes: nothing from `ref/` is tracked.

## Hardware

None.

## If blocked

- **G1 fails** (`ET_EXEC` at a low fixed address): stop. Write the evidence,
  check whether TTR ships any other Linux build, and report. Do not start
  Phase 3 work that only makes sense if G1 passes.
- The engine does not start under stock Box64: reduce to the first failing
  call, search Box64's issues, and report; this is an upstream problem first.
- The engine uses a library with no Box64 wrapper: list it for Phase 8 and
  test `BOX64_EMULATED_LIBS` with the x86-64 library.
