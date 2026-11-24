# Phase 1 — Hardware bring-up and platform probes

Read `CLAUDE.md`, `docs/ARCHITECTURE.md` and `docs/STATUS.md` first.
Depends on Phase 0. Decides gate **G3**.

## Goal

A fast deploy-and-log loop between the Mac and the console, and a probe
program whose report replaces assumptions about the platform with measured
numbers.

## Why now

The architecture rests on constraints read from other projects' source
(C1–C9). They were true for kaiHEN 20261117.1. Measure them on the human's
console and firmware before building on them.

## Read before coding

In `third_party/` or the reference clones: kaiHEN `libkaihen/JIT.md`,
`libkaihen/include/kaihen.h`, `hen/README.md`; libounce's README and the
headers for `jit.h`, `svc.h`, `virtmem.h`; `ounce-examples`; Chromium NX
`gx/host_nx.c` (search for `__SWITCH2__`). Note what you relied on in
`docs/upstream-notes.md`.

## Work

1. **Logging library** (`host/platform/log.*`): line-buffered file log under
   `sdmc:/switch/ttr-nx2/logs/`, flushed after every line; a `stage_begin` /
   `stage_end` pair that writes a marker before and after risky steps; an
   optional TCP sink to the Mac; a redaction filter that every sink passes
   through (unit-tested on macOS now, used from Phase 5 on).
2. **Deploy loop**: `tools/deploy.sh` (FTP upload to OunceShell with `lftp`),
   `tools/pull-logs.sh`, `tools/logserver.py` (prints lines streamed from the
   console). Wire to `make deploy` and `make logs`. Document the SD-card
   reader fallback.
3. **`probe.nro`**: a console-text program that runs a menu of probes and
   writes `logs/probe-report.json`. Each probe records value, pass/fail and
   duration. Probes:
   - identity: firmware version, kaiHEN status and protocol version, how the
     program was started, operation mode (handheld or docked), display size;
   - memory: heap given by the loader; address-space regions (alias, heap,
     stack, ASLR) from `svcGetInfo`; how much physical memory can be mapped
     with `svcMapPhysicalMemory` in 64 MB steps until refusal; how many
     separately mapped 1 MB pieces succeed before the kernel refuses (stop at
     12,000);
   - CPU: cores usable, affinity mask, a fixed integer workload timed per core;
   - JIT: `jitCreate` at 1, 16, 64 and 256 MB; write code that returns 42 to
     staging, publish, execute; time a full publish and
     `kaihenJitPublishRanges` for 4 KB, 64 KB and 1 MB; number of regions
     creatable; a second thread executes code the first published, following
     the synchronisation rule in `JIT.md`;
   - graphics: EGL configs; try a desktop OpenGL compatibility context, a
     core context and GLES 3.2; record `GL_VERSION`, `GL_RENDERER`, shading
     language version, extension list, maximum texture size; draw a triangle
     with fixed-function calls if a compatibility context exists; Vulkan
     device properties;
   - audio: play one second of tone through the audio output service;
   - network: DNS resolution and a TCP connect to port 443 of
     `www.toontownrewritten.com` (connect only, send nothing);
   - input: pad, touch, Joy-Con 2 mouse mode, USB keyboard and mouse if
     attached; software keyboard in text mode and in password mode;
   - storage: sequential write and read of 64 MB, creation of 2,000 small
     files, free space;
   - lifecycle: what the program observes on HOME press, sleep and wake.
   - **destructive probes, opt-in, run last, one per launch:** read an
     unmapped address; execute `mrs x0, cntvct_el0`; request writable and
     executable memory. Before each, write a marker; on the next start the
     probe reads the marker to conclude whether the process survived.
4. **Report**: commit the JSON for handheld and docked under
   `docs/hardware/probe-YYYYMMDD-<mode>.json` and write
   `docs/hardware/probe-summary.md` with a table: constraint, expected
   (from the architecture document), measured, verdict.
5. **Decide G3** in `docs/STATUS.md` with the numbers: guest memory available,
   JIT region size and publish latency, GL path (desktop compatibility
   available or not), record budget.

## Deliverables

Logging library with unit tests, deploy tools, `probe.nro`, hardware
checklist `docs/hardware/phase-01-checklist.md`, probe reports and summary.

## Acceptance criteria

- [ ] Redaction filter unit tests pass on macOS (`make test`), including
      values split across two writes.
- [ ] `make deploy IP=…` followed by `make logs IP=…` completes in under 60
      seconds for a 5 MB NRO (human-timed, recorded).
- [ ] `probe-report.json` exists for handheld and docked, every probe has a
      verdict, and none is "not run" without a stated reason.
- [ ] Each destructive probe's outcome is recorded, and for each one that
      killed the process the last log line names the stage.
- [ ] Generated code executed through the JIT API returned 42 on the main
      thread and on a second thread.
- [ ] `probe-summary.md` marks each of C1–C6 as confirmed, refuted or
      changed, with the measured value.
- [ ] G3 has a written verdict and, if "pass with limits", the limits are
      copied into `docs/STATUS.md` as budgets that later phases must respect.

## Hardware

The whole phase. Write the checklist so that each probe run is: start
`probe.nro` from hbmenu, choose a probe set, wait for "done", run `make logs`.

## If blocked

- A probe refutes a constraint in a favourable way (for example faults are
  now delivered): record it, do not redesign yet, raise it with the human.
- A probe refutes a constraint unfavourably (for example JIT regions are far
  smaller than assumed): stop and report; G3 may fail.
- OunceShell's FTP is unavailable: use the SD-card reader path and note the
  slower loop.
