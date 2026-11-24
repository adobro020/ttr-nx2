# TTR NX2 — research findings and architecture

Researched 2026-11-24 from primary sources (repository READMEs, docs and source
files). Section 7 lists them. Anything marked **ASSUMPTION** was not verified
and has a phase that verifies it. The Switch 2 homebrew stack is less than two
weeks old at the time of writing: re-read the pinned upstream docs before
relying on any detail here, and record changes in `docs/upstream-notes.md`.

## 1. What exists today (verified)

### kaiHEN — `ouncebrew/kaihen` (GPL-2.0-only; `libkaihen/` is ISC)

- A homebrew environment and minimal custom firmware for Switch 2. First public
  release about 2026-11-13; latest tag read: `20261117.1`. News coverage says it
  supports firmware 23.0.1 and earlier (confirm against the release notes).
- Homebrew runs **inside a retail game's process on the stock kernel**. The
  user holds R while starting a native game; from the second such launch the
  game's process starts `hbloader`, which runs `hbmenu`, which runs NROs.
- Components: `ro` (an `ldr:ro` service that maps NROs into clients and
  publishes JIT code), `hen` (resident service: SM proxy, FS root, homebrew
  interface), `bootstrap`, `libkaihen` (homebrew API, JIT provider).
- The release zip ships OunceShell, a file manager **with an FTP server** (SD
  card at the FTP root).
- Upstream warning: homebrew gets full system access including system NAND; a
  bad program can brick the console.
- **JIT model** (`libkaihen/JIT.md`), reached through the libnx-compatible `Jit`
  API when linking `-lkaihen`:
  - `jitCreate` allocates locked backing, a stable RX address in the game
    process, and a **separate RW staging buffer that is not an alias of RX**.
  - `jitTransitionToExecutable` sends the whole staging buffer to RO, which
    copies it into the RX mapping. `kaihenJitPublishRanges` publishes sparse
    ranges in one request.
  - RO records at most **512 live JIT mappings per session**.
  - Staging costs extra physical memory about equal to the region size.
  - Only the calling thread's instruction cache range is invalidated on
    publish. Other threads must synchronise with the publisher and invalidate
    their own range. A block another thread is executing must not be modified.

### libounce, ounce-devkit, OunceVK — `ouncebrew/*`

- libounce is libnx with Switch 2 changes (ISC). In a libnx Makefile, replace
  the include with `include $(DEVKITPRO)/libounce/switch2_rules`; `-lnx` then
  links libounce. CMake: `source $DEVKITPRO/switch2vars.sh` then
  `aarch64-none-elf-cmake`.
- Install: devkitPro pacman plus `sh install.sh` from ounce-devkit (adds the
  `[ounce]` repository at `pkg.ouncebrew.org`), or build the Docker image in
  ounce-devkit (based on `devkitpro/devkita64`).
- OunceVK provides Vulkan, EGL, OpenGL and OpenGL ES (`-lvulkan`, `-lEGL`).
  Chromium NX's source describes its GL path on Switch 2 as Zink over NVK.
- devkitPro portlibs that use only the C library and libnx (SDL2 is named)
  work unchanged.
- Also in the organisation: `ounce-hbloader`, `ounce-hbmenu`, `ounce-examples`,
  `drako3d` (low-level graphics API), `uam2` (shader compiler), `hpak`
  (package manager), `hblist` (homebrew list site).

### Chromium NX — `shodowlo/chromium-nx` (GPL-2.0; fork of `mnnobre/lkl-switch`)

v0.2.0 added Switch 2 support, tested on firmware 23.0.1 with kaiHEN 20261117.1.
It is the closest precedent to this project: it runs **unmodified Debian arm64
Linux binaries inside one Horizon homebrew process**.

- **LKL**: Linux 6.12 built as a library (`ARCH=lkl`, no MMU). Gives a real VFS
  (ext4 image, tmpfs), sockets, pipes, epoll.
- **gx** (guest executor): loads dynamically linked, multi-threaded aarch64
  Linux ELF programs and runs them natively. Every `svc #0` in an executable
  mapping is rewritten into a branch to a trampoline that forwards the Linux
  syscall to `lkl_syscall()`. `gmem.c` implements mmap/munmap/mprotect/brk
  itself over one reserved arena. `nat.c` NATs LKL's network to Horizon
  sockets. `hostfs_nx.c` exposes SD card folders as kernel filesystems.
- Guest `libEGL`/`libGLESv2`/`libasound` are replaced by small libraries that
  call the host's drivers through gx hostcalls (`GX_SYS_HOST_SYMBOL`,
  `GX_SYS_HOSTCALL`, `gx/guest/hostlib.c`).
- The core talks to the platform only through `host_*` functions, so the same
  code runs on a PC (`host_posix.c`, under qemu-user) and on the console
  (`host_nx.c`). `gx/tests/run-switch2-like.sh` runs on the PC under the
  Switch 2's constraints.

**Switch 2 constraints documented in its source** (`gx/host_nx.c`, `gx/gmem.c`,
`gx/gsys.c`). These shape everything below:

| # | Constraint | Consequence for this project |
|---|---|---|
| C1 | **No fault reaches the homebrew.** Any fault ends the process "without a word". | No signal emulation. No fault-driven tricks. On-device crashes carry no information: debug on the PC bench. |
| C2 | A game process has **no code-mapping syscalls**. Executable memory exists only through RO's JIT commands, from heap pages. Never writable and executable at once, and not "by turns" either. | A stock JIT cannot run (Chromium NX runs V8 `--jitless`). A JIT must be ported to the staging/publish model. |
| C3 | **No shared memory** (`svcCreateSharedMemory` is not in the policy). | `MAP_SHARED` views are single copies. |
| C4 | `mrs xN, cntvct_el0` traps and kills the process. gx patches it to `cntpct_el0` in guest code. | Any code generator must emit `cntpct_el0`. |
| C5 | Data lives in the alias region (128 GB of addresses) via `svcMapPhysicalMemory`. ELF images live in a window (≤ 1280 MB) of the 2 GB stack region, backed by a 1024 MB heap pool. | Native ARM64 images are limited in total size and each code segment costs a JIT mapping (see C2's 512 cap). |
| C6 | The kernel keeps a record per run of pages mapped alike; the process stops being served at about ten thousand. gx commits data in 1 MB units. | Memory-map fragmentation is a hard budget. |
| C7 | gx implements `clone` **for threads only**: no fork, no exec. | `subprocess`, `os.system` do not work. |
| C8 | `rt_sigaction`, `rt_sigprocmask`, `sigaltstack` return 0 and do nothing; `kill`/`tgkill` end the process. | Guests that depend on signal delivery misbehave silently. |
| C9 | Once gx takes the heap, the process cannot return to hbmenu; it always ends. | Plan for one process lifetime per play session. |

### Simple TTR Launcher — `mike406/Simple-TTR-Launcher` (MIT, v4.0)

- Files: `main.py` (text menu; calls `main()` at import), `launcher.py`
  (`Launcher` class: accounts, login, 2FA/ToonGuard, queue, start game),
  `patcher.py` (`Patcher`: mirrors, manifest, sha1, bz2, bsdiff), `encrypt.py`
  (`Encrypt`: Argon2id + Fernet), `helper.py` (settings JSON, keyring, retry,
  confirm, clear).
- Requirements: `bsdiff4`, `cryptography`, `keyring`, `pwinput`, `requests`,
  `tqdm`. Uses nested same-quote f-strings, so **Python ≥ 3.12 is required**.
- Terminal-bound I/O points: `input()`, `pwinput.pwinput()`, `print()`,
  `helper.confirm()`, `helper.clear()` (calls `os.system('clear')`),
  `helper.quit_launcher()`, `webbrowser.open()`, `tqdm`/`thread_map`.
- `launcher.json` is stored next to `helper.py` (`get_launcher_path()`).
- Passwords go to the OS keyring by default, or into `launcher.json`
  optionally encrypted with a master password (Argon2id → Fernet).
- `Patcher._get_system()` uses `sys.platform`; `'linux'` selects the Linux
  files. Downloads are staged through `tempfile`.
- `Launcher._start_game()` sets `TTR_GAMESERVER` and `TTR_PLAYCOOKIE` in the
  environment and starts `TTREngine` in the install directory with
  `subprocess.Popen`/`subprocess.run`.

### TTR login API — `ToontownRewritten/api-doc` (`login.md`)

POST to `https://www.toontownrewritten.com/api/login?format=json` with
`username`/`password`. Responses: `success=false` (show `banner`), `partial`
(collect a token, resend `appToken` + `authToken`), `delayed` (wait, resend
`queueToken`), `true` (`gameserver`, `cookie`, `manifest`). The game is booted
with `TTR_GAMESERVER` and `TTR_PLAYCOOKIE`. The patch manifest path is appended
to `https://cdn.toontownrewritten.com`.

A play cookie is a login credential. A public write-up describes account
takeover through leaked log files, so the cookie must never be logged.

### Box64 — `ptitSeb/box64` (MIT)

- A userspace x86-64 Linux emulator for a Linux host. It **wraps** system
  libraries (libc, X11, GL, OpenAL, …) to native host libraries and emulates
  the rest, so it needs a real glibc Linux userland around it.
- Its README states the DynaRec uses memory protection plus a SIGSEGV handler
  to handle self-modifying/JIT code. That mechanism cannot exist under C1/C8.
- Build options seen in `CMakeLists.txt`: `ARM_DYNAREC`, `NOLOADADDR` (do not
  fix Box64's own load address), `STATICBUILD` (marked "not working"),
  `SAVE_MEM`, `BAD_SIGNAL`.
- Settings seen in `docs/USAGE.md`: `BOX64_DYNAREC`, `BOX64_NODYNAREC`,
  `BOX64_NOSIGSEGV`, `BOX64_DYNAREC_DIRTY`, `BOX64_DYNAREC_NOHOTPAGE`,
  `BOX64_DYNAREC_STRONGMEM`, `BOX64_DYNAREC_TEST`, `BOX64_DYNACACHE`,
  `BOX64_LOAD_ADDR` (PIE guests only), `BOX64_MMAP32`, `BOX64_RDTSC_1GHZ`,
  `BOX64_LIBGL`, `BOX64_EMULATED_LIBS`, `BOX64_LD_LIBRARY_PATH`, `BOX64_LOG`.
  Read the pinned version's `USAGE.md` for exact meanings.

### Other precedents

- `mnnobre/lkl-switch`: the original Linux-as-a-library NRO (MIT for its own
  code).
- Autorun (formerly Wine-NX): Wine with Box64/FEX on the **Switch 1** under
  Atmosphère. It shows Box64 can live inside Horizon, but Atmosphère grants
  code-mapping syscalls and user exception handlers that kaiHEN does not.
- kaiHEN already runs RetroArch, Moonlight-nx2 and native recompiled games.

## 2. Options considered

| Option | Verdict |
|---|---|
| **A. gx + LKL as an in-process Linux personality, hosting ARM64 Linux Python and ARM64 Linux Box64** | **Chosen.** The only route that satisfies every stated requirement, and each layer has a working precedent on this console. |
| B. Port Box64 and CPython natively to libounce | Rejected. Box64 needs glibc, `ld.so` and Linux syscalls for its wrapped libraries; prebuilt `cryptography` wheels cannot load; it is not "ARM64 Linux Python". |
| C. Statically recompile TTREngine to ARM64 | Rejected. Not the original binary through Box64, and modifies the client. |
| D. Stream the game (Moonlight) | Rejected. Not the goal. |
| E. Boot Linux | Impossible. No kernel access on Switch 2. |

## 3. Chosen architecture

```
ttr-nx2.nro — one Horizon process (a game's process under kaiHEN, stock kernel)
│
├─ host/                native code, libounce + OunceVK + libkaihen
│  ├─ gui/              graphical login UI, software keyboard, pad and touch
│  ├─ platform/         memory, threads, audio out, sockets, JIT regions, logging
│  └─ bridge/           hostcalls offered to guests: ui, jit, gl, audio, input
│
├─ runtime/             LKL (Linux as a library) + gx (ELF loader, svc patching,
│                       guest memory, syscalls, NAT, SD card filesystems)
│
└─ guests               aarch64 Linux programs, from rootfs.ext4 on the SD card
   ├─ python3.12 ─ adapter ─ Simple TTR Launcher (unmodified source)
   │        │      requests, cryptography, bsdiff4, keyring, tqdm (stock wheels)
   │        └─ execve (in-process image replacement, environment in memory)
   │                 ▼
   └─ box64 (aarch64 Linux build) ── interprets / recompiles ──▶ TTREngine
            │                                   (x86-64, downloaded to the SD
            │                                    card by the launcher's patcher)
            └─ wrapped native libraries: real glibc; libX11 / libGL / audio
               replaced by shim libraries that call the host bridge
```

"Directly on Horizon OS without kernel access" here means: no Linux boot, no
kernel patches, no custom kernel services. Everything is userland code inside
the process kaiHEN gives homebrew.

## 4. Design decisions (seed ADRs; each is validated in the named phase)

1. **Upstream launcher source stays byte-identical.** It is a pinned git
   submodule. `main.py` is not imported (it is only the text menu and runs at
   import). An adapter drives `launcher.Launcher` and replaces the terminal
   I/O points listed in §1 at runtime. (Phase 5)
2. **GUI is native, launcher logic is Python.** They talk over a versioned
   JSON-lines protocol: prompts, answers, status, progress, handoff. (Phases 5–6)
3. **Launching the game is `execve`, implemented in gx as in-process image
   replacement** (stop other guest threads, release guest memory, load the new
   image, keep LKL running). The adapter's `subprocess` shim calls
   `os.execve(box64, [box64, TTREngine], env)`, so the play cookie only ever
   exists in memory. Alternative if this proves unsound: relaunch the NRO
   through the loader with arguments, as Chromium NX's launcher does. (Phase 3)
4. **x86-64 ELF files are data.** gx must never scan or patch them for `svc`
   or counter-read bit patterns and must not place them in the native image
   window. Only aarch64 images get patched and RX-mapped. (Phases 3, 7)
5. **Box64 comes up interpreter-only first**, then gains a dynarec ported to
   kaiHEN's staging/publish JIT. Correctness before speed; the interpreter
   build stays as a permanent fallback and debugging reference. (Phases 7, 10)
6. **No signals, by design.** Box64's protection-fault SMC detection is
   replaced by policy: file-backed x86 text is treated as immutable; x86 code
   in anonymous executable memory is hash-checked on entry. Guest faults end
   the process. (Phase 10)
7. **X11/GLX/audio are shim libraries**, exporting exactly the symbols the
   engine imports, backed by host EGL/GL and audio out. Whether GL is served by
   OunceVK's desktop OpenGL or by a GL-to-GLES translator (gl4es) is decided
   from measurements. (Phases 1, 2, 8)
8. **Stored credentials are always encrypted with a user secret.** Every
   homebrew on a kaiHEN console can read the SD card, and the card is
   removable. No unattended auto-login from disk. (Phase 5)
9. **Three test tiers before hardware:** unit tests on macOS; the PC bench
   (gx with `host_posix` in an arm64 Linux container); the bench in "nx2-like"
   mode that enforces C1–C8. Hardware confirms; it is not where bugs are found.

## 5. Feasibility gates

A gate that fails stops the phase. Report it; do not work around it silently.

| Gate | Question | Decided in | If it fails |
|---|---|---|---|
| G1 | Can TTREngine be loaded at an arbitrary high address? (PIE / `ET_DYN`, no low-4 GB or `MAP_32BIT` dependence) | Phase 2 | No cheap fallback: guest addresses are host addresses in Box64. Project is blocked; write up the evidence. |
| G2 | Does unmodified TTREngine run under stock Box64 on ordinary ARM64 Linux? | Phase 2 | Fix or report upstream first; nothing on the console can work before this does. |
| G3 | Does the console give enough: guest memory, JIT regions, a usable GL, sockets, keyboard applet? | Phase 1 | Re-budget (lower resolution, gl4es path, smaller rootfs) or stop. |
| G4 | Does Python 3.12 with `cryptography` and `requests` run on gx on the console? | Phase 4 | Reduce native extension count; investigate gx gaps. |
| G5 | Does Box64 (interpreter) run real x86-64 programs on gx with no signals? | Phase 7 | Patch Box64's signal and `/proc` assumptions; otherwise stop. |
| G6 | Does the staged-JIT dynarec pass Box64's tests and give ≥ 10× the interpreter? | Phase 10 | Ship as a technical demo, clearly labelled unplayable. |
| G7 | Is the game playable (frame-rate targets in Phase 11)? | Phase 11 | Lower targets, document honestly. |
| G8 | Is public release acceptable to the TTR team's rules? | Before Phase 12 release (human) | Keep the repository private. |

## 6. Main risks

- **G1 is binary and unknown.** Check it before writing any console code.
- **Dynarec port (G6) is the largest engineering item.** Every address the
  ARM64 backend computes from the emit pointer, and every runtime patch of
  emitted code, must be audited for write-address ≠ execute-address.
- **JIT mapping budget is shared.** Each native library's code segment uses
  one of RO's 512 mappings, alongside the dynarec's regions.
- **Embedded Python in the engine may create x86 thunks at run time** (libffi
  closures). Decision 6 covers this; verify it in Phase 2's recon.
- **Silent death on device (C1).** Breadcrumb logging and the nx2-like bench
  are mandatory, not optional.
- **Upstream churn.** kaiHEN's protocol version, JIT limits and policies may
  change weekly. Pin, and re-probe after every bump.
- **Console and account risk.** A kaiHEN console can be bricked by bad
  homebrew and may be banned from Nintendo's online services. TTR may not
  support or permit unofficial platforms. Both are the human's decisions.

## 7. Sources

- kaiHEN: https://github.com/ouncebrew/kaihen (README, `libkaihen/JIT.md`, `hen/README.md`, `ro/README.md`, releases)
- libounce: https://github.com/ouncebrew/libounce
- ounce-devkit: https://github.com/ouncebrew/ounce-devkit
- OunceVK: https://github.com/ouncebrew/ouncevk
- Chromium NX: https://github.com/shodowlo/chromium-nx (README, `gx/gx.h`, `gx/gmem.c`, `gx/gsys.c`, `gx/host_nx.c`, `gx/tests/run-switch2-like.sh`)
- lkl-switch: https://github.com/mnnobre/lkl-switch
- Simple TTR Launcher: https://github.com/mike406/Simple-TTR-Launcher
- TTR API docs: https://github.com/ToontownRewritten/api-doc/blob/master/login.md
- Box64: https://github.com/ptitSeb/box64 (`CMakeLists.txt`, `docs/USAGE.md`)
- Autorun / Wine-NX: https://github.com/autorunhq/autorun/wiki
- News coverage of kaiHEN: https://onejailbreak.com/blog/kaihen-released-as-switch-2-homebrew-environment/ , https://pbxscience.com/kaihen-brings-the-first-public-homebrew-environment-to-nintendo-switch-2/
