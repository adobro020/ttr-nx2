# Phase 7 — Box64 on gx, interpreter only

Read `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/STATUS.md`,
`docs/runtime-notes.md` and the Phase 2 recon first. Depends on Phase 3.
Can run in parallel with Phases 4–6. Decides gate **G5**.

## Goal

An aarch64 Linux build of Box64, with its dynamic recompiler switched off,
runs x86-64 Linux test programs as a guest of gx on the bench, in nx2-like
mode and on the console.

## Why interpreter first

The interpreter needs no executable memory at all, so it isolates every
problem that is not the JIT: loading, memory layout, wrapped libraries,
threads, missing syscalls, the absence of signals. It also remains the
reference the recompiler is checked against in Phase 10.

## Read before coding

At the pinned Box64 commit: `docs/USAGE.md`, `docs/COMPILE.md`,
`CMakeLists.txt`, the start-up path, the ELF loader, the custom memory
manager (how it finds free address ranges and whether it reads
`/proc/self/maps`), signal set-up, thread creation, and how wrapped libraries
are located and opened. Write `docs/box64-notes.md` with file and function
names for each.

## Work

1. **Build** in `docker/bench-arm64` from `third_party/box64` with a build
   directory under `box64/`: generic ARM64, recompiler off
   (`ARM_DYNAREC=OFF`), position-independent with `NOLOADADDR=ON` so gx
   chooses the address. `STATICBUILD` is marked not working upstream; do not
   rely on it. Keep our changes as a numbered patch series in
   `box64/patches/`, each with a reason and whether it could go upstream.
2. **Start-up audit against gx**, fixing in the runtime where the behaviour
   is ordinary Linux and in a Box64 patch where it is a policy choice:
   - signals: handler installation succeeds and does nothing (C8); make sure
     no start-up step waits for a signal; set `BOX64_NOSIGSEGV` and related
     settings as documented;
   - memory discovery: if Box64 reads `/proc/self/maps` or probes with
     `mmap` hints, give it a truthful view of the guest arena (gx can
     synthesise the file from its page table);
   - `mmap` flags it uses (`MAP_FIXED_NOREPLACE`, `MAP_NORESERVE`,
     `MAP_32BIT`, hints) and its reservations of low or high memory: support
     them or make Box64 accept refusal;
   - `/proc/cpuinfo`, `/proc/self/exe`, `sched_getaffinity`, `prctl`,
     `personality`, `membarrier`, `rseq`, timers and event descriptors: route
     to LKL, synthesise, or stub, with a note for each;
   - the x86-64 image rule from Phase 3 holds for everything Box64 maps.
3. **x86-64 support libraries**: install the x86-64 runtime libraries Box64
   expects to emulate rather than wrap (its bundled `libstdc++` and
   `libgcc_s`, per its docs) into the rootfs, with licences recorded.
4. **Configuration**: a `box64rc` profile in the rootfs for our use: logging
   level, library paths, recompiler off, no banner. Every setting has a
   comment saying why and cites `USAGE.md`.
5. **x86-64 test programs** (`tests/guest/x86_64/`, built in
   `docker/ref-amd64`, all original code): static and dynamic hello; threads
   with thread-local storage and mutex contention; floating point, SSE and
   x87 results against known values; a memory allocator stress; sockets
   through the fake server; `dlopen` of an x86-64 library; C++ exceptions and
   `std::thread`; `setjmp`/`longjmp`; time sources including `rdtsc`; file
   I/O on the `game/` mount; a program that installs a signal handler and
   continues (it must not hang); a CPU benchmark of your own writing with a
   printed score.
6. **Box64's own test suite**: run it through gx on the bench and in nx2-like
   mode. Classify every failure: needs signals (expected skip, listed),
   needs fork or exec (expected skip), runtime gap (fix), unknown (issue).
7. **Measure**: benchmark score natively in the container, under stock Box64
   with the recompiler, under stock Box64 interpreter, and under our build on
   gx. The last two should be close; a large gap means runtime overhead to
   find.

## Deliverables

Box64 build recipe and patch series, `docs/box64-notes.md`, x86-64 tests,
classified upstream test results, measurements in `docs/perf/box64.md`,
`docs/hardware/phase-07-checklist.md`.

## Acceptance criteria

- [ ] `make bench` and `make test-nx2like` pass every program in
      `tests/guest/x86_64/`; show both summaries.
- [ ] Box64's test suite: pass count reported for both modes; every
      non-passing test has a classification and none is "unknown".
- [ ] In nx2-like mode the run requests no executable-and-writable memory and
      no shared memory (constraint counters are zero), and memory-record and
      JIT-mapping peaks are under budget.
- [ ] Our interpreter build on gx scores within 15% of stock Box64's
      interpreter on the same container.
- [ ] Each patch in `box64/patches/` applies cleanly to the pinned tag and
      states its reason.
- [ ] Hardware (pending human until logged): the same x86-64 test list
      passes on the console; the benchmark score is recorded; G5 is marked in
      `docs/STATUS.md`.

## Hardware

Deploy, run the x86-64 test list from the test menu, pull logs. Ten minutes.

## If blocked

- Box64 depends on a delivered signal for correct operation in interpreter
  mode: find the exact use, and replace it with a synchronous check in a
  patch. If it cannot be removed, G5 fails; report.
- Address-space layout conflicts (Box64 wants ranges the arena cannot give):
  compare with Phase 1's region map and adjust the arena windows before
  touching Box64.
