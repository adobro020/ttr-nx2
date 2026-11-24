# Phase 3 — The Linux runtime: gx and LKL

Read `CLAUDE.md`, `docs/ARCHITECTURE.md` and `docs/STATUS.md` first.
Depends on Phases 0–2 (G1 and G3 must not have failed).

## Goal

Our own build of the gx runtime that runs small aarch64 Linux programs on the
PC bench, on the bench under Switch 2 constraints, and on the console, with
the two additions this project needs: `execve` and the hostcall bridge.

## Why now

Python and Box64 are both guests of this runtime. Its gaps must be found with
ten-line test programs, not with a game engine.

## Read before coding

All of `third_party/chromium-nx/gx/`: `gx.h` first, then `gmem.c`, `gelf.c`,
`gsys.c`, `tramp.S`, `host_posix.c`, the Switch 2 sections of `host_nx.c`,
`nat.c`, `hostfs_nx.c`, `guest/hostlib.c`, the build scripts and `tests/`.
Write `docs/runtime-notes.md`: how a guest is loaded, how syscalls are
routed, how memory is laid out on each host, what each `__SWITCH2__` block
does and why.

## Work

1. **Import** the runtime into `runtime/`: the gx core, LKL glue, NAT,
   hostfs, `host_posix.c`, and the parts of `host_nx.c` that are platform
   services (memory, threads, time, sockets, storage, logging). Leave out the
   browser: Wayland compositor, overlay, debugging pipe, video, launcher,
   updater. Keep copyright headers and record provenance per file in
   `THIRD_PARTY.md`. Build LKL at a pinned commit with a recorded config.
2. **PC bench** in `docker/bench-arm64`: build gx with `host_posix` and run
   upstream's tests (`hello`, `threads`, `timers`, `net`, `dl`). On Apple
   silicon the container is native arm64, so run without qemu-user where the
   host layer allows it, and say which mode is used.
3. **nx2-like mode** for the bench (`make test-nx2like`), enforcing the
   measured constraints from Phase 1 rather than emulating around them:
   no shared memory; any request for writable-and-executable memory is
   refused and logged; no signal delivery; a memory-record budget counter
   that fails the run when exceeded; a JIT-mapping counter capped at the
   measured limit; image-window and pool sizes as on the console; guest code
   that reads `cntvct_el0` fails the run unless patched. A violation prints
   the constraint number and aborts, so the bench is loud where the console
   is silent.
4. **x86-64 images are data** (architecture decision 4). In `gmem`/`gelf`:
   decide by ELF machine type of the mapped file; never patch, never place in
   the native image window, never count against JIT mappings. Test with an
   x86-64 file containing the `svc #0` and counter-read bit patterns: its
   bytes must be unchanged after an executable `mmap`.
5. **`execve`** as in-process image replacement (architecture decision 3):
   stop and reap all other guest threads, close close-on-exec descriptors,
   release guest memory to the baseline, load the new image and interpreter,
   build the new stack with arguments, environment and auxiliary vector, keep
   the kernel and mounted filesystems. Write the ADR for it first, including
   what happens to host threads serving the old guest. If it proves
   unsound, document why and switch to relaunching the NRO through the loader.
6. **Hostcall bridge**: a registry in `host/bridge/` and a guest library
   `guest/shims/libnx2host.so` with a stable, versioned C interface for later
   phases (`ui`, `jit`, `gl`, `audio`, `input` namespaces; only a `ping` and a
   log call implemented now). Bench and console hosts both implement it.
7. **Standard descriptors**: guest stdout and stderr go to the host log
   through the redaction filter; stdin and two extra descriptors can be backed
   by host-provided pipes (the GUI protocol will use them).
8. **Console build**: `ttr-nx2.nro` starts the runtime, mounts a minimal
   `rootfs.ext4` (busybox-free: just the test programs and their libraries)
   and the `data/`, `game/`, `cache/` folders through hostfs, runs a test
   list from a text file, and writes results to the log with breadcrumbs.
9. **Gap list**: from Phase 2's syscall list, mark each syscall as handled by
   LKL, handled by gx, or missing; implement or stub the missing ones that
   are cheap, and file issues for the rest.

## Deliverables

`runtime/` with provenance, bench and nx2-like test targets in CI, `execve`,
bridge skeleton, console test build, `runtime-notes.md`, the `execve` ADR, syscall
gap table, `docs/hardware/phase-03-checklist.md`.

## Acceptance criteria

- [ ] `make bench` passes upstream's five tests plus ours; show the summary.
- [ ] `make test-nx2like` passes the same list. A deliberately violating test
      program for each of C1–C4 and C6 aborts with the right constraint named.
- [ ] The x86-64 data test shows identical checksums before and after mapping.
- [ ] `execve` test: guest A (with three extra threads and 256 MB allocated)
      execs guest B, which prints an environment variable's presence and its
      thread count of 1. Repeated 100 times in one process, committed guest
      memory at the end is within 1 MB of the first iteration.
- [ ] Network test on the bench: DNS lookup and an HTTPS-port TCP connect
      through LKL and the NAT.
- [ ] CI runs bench and nx2-like suites on an arm64 runner; link the run.
- [ ] Hardware (pending human until logged): the console log shows hello,
      threads, timers, network, `dl`, the x86-64 data test and the `execve`
      test passing, with peak memory records and JIT mappings printed and
      under the Phase 1 budgets.

## Hardware

Deploy `ttr-nx2.nro` and the test `rootfs.ext4`, start from hbmenu, wait for
"tests done", pull logs. One run handheld, one docked.

## If blocked

- A test passes on the bench and dies silently on the console: the nx2-like
  mode is missing a constraint. Find it with breadcrumbs, add it to the mode,
  reproduce on the bench, then fix.
- LKL does not build at the pinned commit: use the commit Chromium NX's build
  script uses and record it.
