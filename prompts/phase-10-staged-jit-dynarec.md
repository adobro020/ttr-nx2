# Phase 10 — Box64's recompiler on kaiHEN's staged JIT

Read `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/STATUS.md`,
`docs/box64-notes.md` and the Phase 1 JIT measurements first.
Depends on Phase 7 (and benefits from Phase 9). Decides gate **G6**.

This is the hardest phase. Take it in the order given, and write the design
before the code.

## Goal

Box64's ARM64 dynamic recompiler runs under the console's rules: generated
code is written to a staging buffer, published to a separate execute-only
mapping, and never depends on a fault being delivered.

## The rules it must obey

From kaiHEN's `libkaihen/JIT.md` and the constraint table (re-read both at
the pinned versions):

- write address ≠ execute address; the staging buffer is not an alias;
- code becomes executable only when published (a call to another process);
  publishing sparse ranges in one request is available;
- at most 512 mappings per session, shared with every native library's code;
- staging doubles the memory of each region;
- publish invalidates the instruction cache for the calling thread only;
  every other thread must synchronise and invalidate before entering new code;
- a block must not be modified while another thread executes it;
- no fault is delivered: no protection-trap detection of self-modifying code,
  no signal for a guest null dereference or divide error;
- generated code must not read `cntvct_el0`.

## Work

1. **Design document and ADR** (`docs/jit-design.md`) before any code:
   region layout (a small number of large regions, sized from Phase 1);
   allocation inside regions; when to publish (per block, or batched) with
   the measured latency; the cross-thread protocol (for example a global
   publish epoch that each thread compares on dispatch, invalidating the
   published ranges it has not yet seen); block invalidation and memory
   reuse; the self-modifying-code policy; what happens on guest faults.
2. **`nx2jit` interface** in the hostcall bridge and `libnx2host`:
   create region, get staging and execute bases, publish ranges, invalidate
   for this thread, statistics. Console implementation over libounce's `Jit`
   API and `kaihenJitPublishRanges`. **Bench implementation that reproduces
   the rules exactly**: a separate staging buffer, an execute-only mapping,
   copy on publish, optional injected latency equal to the console's, the
   mapping cap, and per-thread tracking so that a thread entering code it
   has not invalidated is reported as an error.
3. **Audit the ARM64 backend** at the pinned commit and record every finding
   in `docs/jit-design.md`:
   - every place that derives an address from the emit pointer (PC-relative
     literals, the per-block constant table, branches between blocks, return
     address prediction, pointers stored in block metadata and the jump
     table): each must use the execute address while writing through the
     staging address;
   - every place that writes into already-emitted code or its inline data at
     run time (linking, invalidation marks, hot patching): each must go
     through staging and publish, or move the mutable datum into ordinary
     writable memory;
   - every use of memory protection and the fault handler;
   - every emitted system-register read.
4. **Port** as a patch series on top of Phase 7's: an emit abstraction with
   separate write and execute cursors; allocation from `nx2jit` regions;
   publish at block completion; the thread protocol; `cntpct_el0`.
5. **Self-modifying code without faults**: file-backed x86-64 text is
   treated as immutable. Blocks translated from anonymous executable memory
   (thunks and closures created at run time, which Phase 2's recon looked
   for) verify a hash of their source bytes on entry. Read how Box64's
   existing settings for dirty and always-tested blocks work in `USAGE.md`
   and the code, and build on that mechanism rather than inventing another.
   Guest writes to file-backed text are not detected; document this limit.
6. **Verification on the bench, in nx2-like mode**:
   - Box64's recompiler-versus-interpreter comparison mode
     (`BOX64_DYNAREC_TEST`) over the Phase 7 programs and Box64's test suite;
   - a multi-threaded stress where eight threads execute and trigger
     translation continuously for ten minutes;
   - a self-modifying x86-64 test in anonymous memory (must run correctly)
     and one in file-backed text (documented as unsupported);
   - the benchmark from Phase 7 for speed.
7. **Tuning**: publish batching, region count, and the memory-ordering and
   block-size settings (read `USAGE.md`) for a multi-threaded game.
8. **Translation cache** (stretch): Box64's on-disk cache of translated
   blocks can remove warm-up on later starts. It needs stable load addresses
   for the guest and for the regions; evaluate, and implement only if the
   audit shows it is safe under the staged model.
9. **Engine run**: repeat Phase 9's bench rehearsal and hardware session
   with the recompiler on, and record the same measurements.

## Deliverables

`docs/jit-design.md`, ADR, `nx2jit` on bench and console, Box64 patch
series, verification suite in CI, measurements, a profile switch between
interpreter and recompiler, `docs/hardware/phase-10-checklist.md`.

## Acceptance criteria

- [ ] The audit lists every site in each of the four categories with file
      and function, and each has a disposition (changed, moved, not needed).
- [ ] Bench nx2-like: the comparison mode reports no divergence across the
      Phase 7 programs; Box64's test suite passes at least the set that
      passed under the interpreter.
- [ ] The bench JIT layer reports zero rule violations (no write to execute
      mappings, no entry without invalidation, mapping count under the cap)
      across the whole suite, including the ten-minute thread stress.
- [ ] Benchmark score with the recompiler is at least ten times the
      interpreter score on the bench.
- [ ] JIT regions use no more than 16 mappings; the total including native
      libraries is reported and under the cap with margin; staging memory
      overhead is reported.
- [ ] The interpreter profile still passes its suite (no regression).
- [ ] Hardware (pending human until logged): the Phase 7 x86-64 tests and
      benchmark pass with the recompiler; publish count and latency
      statistics are in the log; the engine reaches a playground and runs
      thirty minutes; frame rates are recorded beside the interpreter
      baseline; G6 is marked in `docs/STATUS.md`.

## Hardware

Two sessions: tests and benchmark, then the engine.

## If blocked

- Publish latency makes per-block publishing too slow: batch at dispatch
  boundaries; interpret a block until its translation is published.
- A category of run-time code patching cannot be removed: keep those blocks
  on the interpreter and measure the cost.
- The thread protocol cannot be made sound: stop and write up why; a
  single-translator-thread design is the fallback to evaluate with the human.
- G6 fails: the project can still ship as a labelled technical demo. That is
  the human's decision.
