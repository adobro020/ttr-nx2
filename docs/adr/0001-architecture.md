# 0001 — Architecture: gx + LKL in one Horizon process

Date: 2026-11-24. Status: accepted (Phase 0). Evidence: `docs/ARCHITECTURE.md`.

## Context

The goal is to run the unmodified Simple TTR Launcher (Python 3.12 with stock
`cryptography`, `requests`, `bsdiff4`, `keyring`, `tqdm`) and the original
Linux x86-64 `TTREngine` on a Switch 2 under kaiHEN, in userland, with the
stock kernel. kaiHEN homebrew runs inside a retail game's process with no
code-mapping syscalls, no fault delivery, no shared memory and JIT only
through RO's staging/publish model (constraints C1–C9).

## Options

A. gx + LKL as an in-process Linux personality hosting aarch64 Linux CPython
   and aarch64 Linux Box64. B. Port Box64 and CPython natively to libounce.
C. Statically recompile TTREngine. D. Stream the game. E. Boot Linux.
(Detail in `docs/ARCHITECTURE.md` §2.)

## Decision

Option A. One Horizon process: a native host layer (libounce, OunceVK,
libkaihen) for GUI, platform services and a hostcall bridge; LKL plus
Chromium NX's gx loading aarch64 Linux ELF guests from an ext4 image; the
launcher driven by an adapter over a JSON-lines protocol; "start the game"
becomes an in-process `execve` into Box64, which runs `TTREngine`; X11, GLX
and audio are guest shim libraries over the bridge; Box64 starts
interpreter-only, then gets its ARM64 dynarec ported to the staged JIT.

## Consequences

- Only option A meets every requirement, and every layer has a precedent on
  this console (Chromium NX runs Debian arm64 binaries in one process).
- The project depends on gates G1–G8; G1 (TTREngine loadable at a high
  address) and G6 (dynarec under staged JIT) can end it.
- Everything is designed around C1–C9: no signals, no W+X, a 512-mapping JIT
  budget, ~10k memory-map records, no fork/exec, silent faults. Hence the
  PC bench with an nx2-like mode and mandatory breadcrumb logging.
- The licence is GPL-2.0-only because gx and LKL are GPL-2.0.
- Seed decisions 1–9 in `docs/ARCHITECTURE.md` §4 each get their own ADR
  when the phase that validates them runs.
