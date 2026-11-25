# TTREngine `91bff107` — reference facts (Phase 2)

Linux build fetched 2026-11-24 by `make fetch-game` (the launcher's own
patcher, manifest `/content/patchmanifest.txt`). The engine identifies itself
as `ttr-live-v4.4.5`, client revision `h` (its own console output). Facts
only: no disassembly, no copies of game data. Raw output is reproducible with
`make recon-static` (`build/recon/`) and `make recon-run` (`build/recon-run/`).

## 1. Files shipped for Linux

| File | Size | SHA-1 | Kind |
|---|---|---|---|
| `TTREngine` | 48,975,744 | `91bff107359ae3d51e447f4061eebcb6b955bc70` | x86-64 PIE executable, stripped |
| `libopenal.so.1` | 1,212,280 | `05abeb21ffa0a9d36d54ce8f719c6529baf5396a` | x86-64 shared object (OpenAL Soft), not stripped |
| `TTRGame.vlt` | 13,353,127 | `d73bb164…` | data |
| `phase_*.mf`, `winter_*.mf` (17 files) | 0.6 GB together | — | Panda3D multifiles (data) |

The patcher writes every file without execute bits; the launcher adds them to
`TTREngine` just before starting it (launcher.py:281).

`file`: `ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV), dynamically
linked, interpreter /lib64/ld-linux-x86-64.so.2, for GNU/Linux 3.2.0`.
`.comment`: GCC 7.5.0 (Ubuntu 18.04) objects, Ubuntu clang 16.0.6, linked by
Ubuntu LLD 16.0.6. The engine's console output shows Panda3D (`glxGraphicsPipe`,
PRC config variables) with embedded, compiled Python modules.

## 2. ELF facts and gate G1

`readelf -h ref/game/TTREngine`:

```
  Type:                              DYN (Position-Independent Executable file)
  Machine:                           Advanced Micro Devices X86-64
  Entry point address:               0x88d000
```

`readelf -lW ref/game/TTREngine` (LOAD, TLS, RELRO, STACK):

```
  Type           Offset   VirtAddr           PhysAddr           FileSiz  MemSiz   Flg Align
  LOAD           0x000000 0x0000000000000000 0x0000000000000000 0x88be34 0x88be34 R   0x1000
  LOAD           0x88c000 0x000000000088d000 0x000000000088d000 0x2499230 0x2499230 R E 0x1000
  LOAD           0x2d25230 0x0000000002d27230 0x0000000002d27230 0x09d658 0x09d658 RW  0x1000
  LOAD           0x2dc28a0 0x0000000002dc58a0 0x0000000002dc58a0 0x0f1b38 0x246eb9 RW  0x1000
  TLS            0x2d25230 0x0000000002d27230 0x0000000002d27230 0x000008 0x000030 R   0x8
  GNU_RELRO      0x2d25230 0x0000000002d27230 0x0000000002d27230 0x09ddd0 0x09ddd0 R   0x1
  GNU_STACK      0x000000 0x0000000000000000 0x0000000000000000 0x000000 0x000000 RW  0
```

Image span 0x0 – 0x300c759 (48 MiB), all relative to a load base of 0.
`readelf -d`: `FLAGS_1: PIE`, `RUNPATH: [.]`, no `TEXTREL`, no
`FLAGS`/`STATIC_TLS`. Relocation types (`readelf -r`):

| Count | Type |
|---|---|
| 84,399 | `R_X86_64_RELATIVE` |
| 911 | `R_X86_64_JUMP_SLOT` |
| 34 | `R_X86_64_GLOB_DAT` |
| 26 | `R_X86_64_64` |

No `R_X86_64_32`/`32S`/`PC32` against symbols, no copy relocations, no TLS
relocations (the executable's 0x30-byte TLS block is local-exec).
Bundled `libopenal.so.1`: `ET_DYN`, base 0, relocations `RELATIVE` 1468,
`JUMP_SLOT` 169, `64` 35, `GLOB_DAT` 20, `DTPMOD64` 3, `DTPOFF64` 2 (global
dynamic TLS, 10-byte block), no `TEXTREL`.

Dynamic evidence: the start-up syscall trace (`strace -f`, to the title
screen) has **no `MAP_32BIT`** anywhere; stock Box64 maps the image at
**`0x100000000`** (`/proc/<pid>/maps`: `100000000-10088c000 r--p … TTREngine`,
`10088d000-102d27000 r-xp …`), i.e. at a base Box64 chose, and the engine
runs from there to its title screen.

**G1: passed.** `ET_DYN` PIE with all segments relative to base 0, only
position-independent relocation types, no `TEXTREL`, no `MAP_32BIT` seen at
run time, and it runs when loaded at 4 GiB. Remaining caveat: a low-4 GB
dependence that only shows in-game (after login) cannot be ruled out until
the human run; nothing points to one.

Section sizes (`readelf -S`): `.text` 0x24958f7 (36.6 MiB), `.rodata`
0x3ad420 (3.7 MiB), `.eh_frame` 0x278174, `.rela.dyn` 0x1eee08 (2.0 MiB),
`.data.rel.ro` 0x9c7c0, `.data` 0xefea8, `.bss` 0x155379, `.plt` 0x3900.
`.note.stapsdt` holds libstdc++ SystemTap probes.

## 3. Needed libraries and imports

`DT_NEEDED` (in order): `libm.so.6`, `libutil.so.1`, `libopenal.so.1`,
`libOpenGL.so.0`, `libGLX.so.0`, `libX11.so.6`, `libXext.so.6`, `librt.so.1`,
`libdl.so.2`, `libpthread.so.0`, `libgcc_s.so.1`, `libc.so.6`,
`ld-linux-x86-64.so.2`. GL comes through **GLVND** (`libOpenGL` + `libGLX`),
not `libGL.so.1`.

Undefined dynamic symbols by providing library (`tools/ref/imports_by_lib.py`;
version-need index for versioned ones, defining library for the rest; full
names in `engine-91bff107-imports.txt`):

| Library | Imports |
|---|---|
| libc.so.6 | 447 |
| libX11.so.6 | 179 |
| libOpenGL.so.0 | 86 |
| libpthread.so.0 | 73 |
| libm.so.6 | 67 |
| libopenal.so.1 | 26 |
| libGLX.so.0 | 14 |
| libgcc_s.so.1 | 11 |
| libdl.so.2 | 5 |
| libutil.so.1 | 2 |
| librt.so.1 | 2 |
| ld-linux-x86-64.so.2 | 1 |
| libXext.so.6 | 0 (needed, nothing imported) |
| weak, unresolved | 12 (`_ITM_*`, `__gmon_start__`, `ZSTD_trace_*`, `_ZGTt*`) |
| **total** | **925** |

glibc versions required: up to `GLIBC_2.27` (libc, libm), `GCC_4.2.0`
(libgcc_s). Bundled `libopenal.so.1` needs `libdl`, `libatomic`, `libm`,
`libstdc++`, `libgcc_s`, `libpthread`, `libc`, `ld-linux` (204 imports).

Libraries opened at run time (`dlopen`): library names in the binary's
strings are `libGL.so`, `libGLX.so.0`, `libOpenGL.so.0`, `libXcursor.so.1`,
`libXi.so.6`, `libXrandr.so.2`, `libXxf86dga.so.1` plus the needed ones.
Observed under Box64 (`BOX64_LOG=1`): `libXcursor`, `libXi`, `libXrandr`,
`libXrender`, `libXfixes`, `libxcb`, `libXau`, `libXdmcp`, `libbsd` loaded
as wrapped native libraries; **`libXxf86dga.so.1` fails** (`Error loading
needed lib`, Box64 has no wrapper and no x86-64 copy is present) and the
engine carries on. The engine also resolves **174 GL/GLX entry points with
`glXGetProcAddress`** (all resolved by Mesa; list in the imports file),
including `glXCreateContextAttribsARB`, `glXCreateNewContext`, FBO, VAO,
`glTexStorage*`, 3D textures and `glDispatchCompute`; 40 of them are
shader/program/uniform calls.

## 4. Behaviour under stock Box64 on arm64 Linux (gate G2)

Set-up (ADR 0005): `docker/bench-arm64` (Debian 12 arm64, Apple M-series
host, 6 vCPU), stock Box64 v0.4.4 (`-DARM64=ON -DARM_DYNAREC=ON`), Xvfb
1280×720×24, Mesa llvmpipe, ALSA null device, `--network none`. Runs
(`make recon-run …`) with no login:

| Environment | Result |
|---|---|
| no `TTR_PLAYCOOKIE` | prints `Hey there! If you want to play Toontown Rewritten, please log in using the official launcher!` and exits at once |
| `TTR_GAMESERVER=127.0.0.1:9`, placeholder cookie (`FAKE_SERVER=1`) | starts, `Successfully opened window of type glxGraphicsWindow (OpenGL)`, `Using default OpenAL device`, loads fonts and the `init` block, shows the **title screen** ("press any key"), keeps rendering until stopped. It connects to the game server only after the key press. |
| same, `BOX64_DYNAREC=0` | same screens, slower start (below) |
| same, `MESA_GL_VERSION_OVERRIDE=2.1` and `=1.5` | title screen renders the same |
| under `strace` from the start | exits with status 1 about 5 s in, see §5 (`PTRACE_TRACEME`) |
| `LD_PRELOAD` set (apitrace) | Box64 tries to load the preload as an x86-64 library and fails; the engine prints `Starting game` and exits with status 0 within 5 s |

The engine also tried, and failed offline, to resolve an NTP pool, fetch
`https://toontownrewritten.com/api/status`, and open Discord IPC sockets
(`/tmp/discord-ipc-0`, `/tmp/app/com.discordapp.Discord/discord-ipc-0`);
none of these stopped it. It watches `/dev/input` with inotify for
controllers (`Error adding inotify watch on /dev/input` in a container);
`settings.json` has `controller.controller-enabled`.

**G2: passed up to the title screen** with stock Box64 (dynarec and
interpreter), unmodified engine and data. **Pending the human's logged-in
run** (`docs/recon/human-run.md`): login hand-off, connection to the game
server, toon selection.

### Measurements at the title screen (offline)

`samples.txt` (every 5 s from `/proc`), Mesa `GALLIUM_HUD=fps` dump,
per-thread CPU from `/proc/<pid>/task/*/stat` at the end of the run. CPU
includes llvmpipe's rendering threads, which dominate at this screen.

| | Dynarec (`BOX64_DYNAREC=1`) | Interpreter (`BOX64_DYNAREC=0`) |
|---|---|---|
| all 20 threads up | by 10 s | by 155 s |
| `init` block loaded (engine log) | 2.6 s | 37.8 s |
| frames per second (last 60 s) | 49.9 (68–72 in an earlier run) | 38.8 |
| process CPU (last 60 s) | 5.6 cores | 4.7 cores |
| CPU per frame (all threads) | 113 ms | 122 ms |
| CPU over the whole run: engine threads / llvmpipe threads | 93 s / 352 s (95 s run) | 492 s / 558 s (426 s run) |
| threads | 20 = 14 `TTREngine` + 6 `llvmpipe-N` | 20 |
| peak resident memory (VmHWM) | 590 MB | 376 MB |
| `/proc/<pid>/maps` lines | 629 | 125 (sampled earlier in the run) |

The interpreter-only figure per frame of *emulated* work cannot be separated
from llvmpipe at this light screen; the in-game interpreter baseline needs
the human run (`make human-run MODE=interp`). Phase 10's ≥ 10× target should
be measured in-game, not here.

### Logged-in runs (the human, 2026-11-24)

Two logins by the human with their own account through `make human-run`
(`docs/recon/human-run.md`): the unmodified launcher, then stock Box64
v0.4.4 running the engine, Mesa llvmpipe in Xvfb, no strace. Source:
`build/human-run/<mode>/` on the development Mac (git-ignored; to be
deleted once read).

| | Dynarec (`MODE=dynarec`) | Interpreter (`MODE=interp`) |
|---|---|---|
| login to TTR's game server | `Successfully connected`, `Successful login` | same |
| toon selection screen (`AvatarChooser.enter` in the engine log) | reached | reached |
| connection | stable | **lost once**: `Last heartbeat sent from client was sent 6.0383 seconds ago`, then `Lost connection to server`; the engine reconnected (`Successful reconnection`) and returned to the toon selection screen |
| exit | `Exiting cleanly`, `Normal exit.` (game's own Quit) | same |
| length of the session (fps samples, one per second) | 231 s | 745 s (both left open longer than the 60 s asked for, so these are not times to reach the screen) |
| fps, first 10 s | 6.5 | 2.8 |
| fps, last 60 s (toon selection screen) | avg 35.7, min 0.8 | avg 19.4, min 0.3 |
| fps, whole run | avg 39.1, max 68.3 | avg 39.2, max 100.4 |
| 30 s averages | 41 32 47 44 37 41 39 29 | 6 23 18 29 15 21 22 25 17 24 13 25 15 26 25 76 81 84 89 91 89 90 34 25 15 |

- **G2 passes logged in, in both modes.** Unmodified engine and data, stock
  Box64, from login to the toon selection screen and a clean exit.
- **The interpreter missed the server's heartbeat once.** The client went
  about 6 s without sending one and the server dropped the connection; the
  engine reconnected by itself. When it happened (while loading, or while
  waiting at the toon selection screen) is not known: the logs have no
  timestamps. Either way an interpreter-only build on the console
  (Phase 7), which will be slower, must expect it.
- The 80–90 fps stretch near the end of the interpreter run is probably
  the lost-connection dialog or the idle toon selection screen; without
  timestamps it cannot be tied to either.
- Time from login to the toon selection screen was not measured (the
  sessions were left open longer than needed and the logs have no
  timestamps). A later run can add timestamps to `engine.log`.
- Not measured: memory and thread samples. `samples.txt` stayed empty in
  both runs because `human_run.py` replaces `subprocess.run` to catch the
  game start, and its sampler used `subprocess.run` to find the engine.
  Fixed (the sampler reads `/proc`); not re-run.
- The frame rate at the toon selection screen mostly measures llvmpipe
  (software rendering), as at the title screen; the per-frame cost of
  emulation is still not separated.

## 5. Dependency list for Phases 7–9

From `strace -f` of the Box64 process (host arm64 syscalls — what gx must
serve), run to the title screen with `PTRACE_TRACEME` answered 0 by strace's
fault injection (`STRACE=count|trace TRACEME_OK=1`, ADR 0005), 120 s.

### Syscalls (77 distinct; counts from `strace -c`)

Hot: `futex` 721,339; `read` 292,177 and `lseek` 292,115 (data files);
`getpid` 54,823; `recvmsg` 41,324 (X11); `rt_sigprocmask` 36,007; `ppoll`
16,587; `mprotect` 12,899; `rt_sigaction` 8,357; `writev` 8,295; `write`
5,022; `ioctl` 4,276; `mmap` 1,724; `brk` 1,108; `openat` 826.

Also used: `newfstatat munmap close fcntl readlinkat faccessat2 faccessat
set_robust_list rseq clone madvise getcwd connect getdents64 socket uname
prctl getrandom recvfrom umask mkdirat getuid geteuid getgid getegid
shutdown dup dup3 prlimit64 unlinkat sched_get_priority_min
sched_get_priority_max sched_setscheduler sched_getaffinity shmctl shmget
shmat shmdt setsockopt set_tid_address clock_nanosleep execve wait4 pipe2
utimensat gettid sysinfo sendmsg sendto getpeername inotify_init1
inotify_add_watch symlinkat renameat ftruncate pread64 fdatasync
personality clock_gettime ptrace rt_sigreturn getppid memfd_create`.

Notes for gx:

- **`ptrace(PTRACE_TRACEME)` must return 0.** The engine calls it once
  (≈4 s in, after loading) and exits with status 1 if it fails (`= -1 EPERM`
  under strace, then `exit_group(1)` 0.5 s later). With the call answered 0
  it runs normally. On ordinary Linux it succeeds and makes the parent (the
  launcher) its tracer, which is also why nothing can attach to a running
  engine (`TracerPid` = parent). On the console the call takes this path:
  Box64 translates the engine's x86-64 syscall to aarch64 (not yet checked
  how it handles ptrace), then gx, which has no ptrace case of its own and
  forwards unhandled syscalls to LKL (`return lkl_syscall(nr, params);`,
  `gx/gsys.c` line 693 at chromium-nx v0.2.0). Whether LKL answers 0,
  `-EPERM` or `-ENOSYS` is **untested**: it depends on whether ptrace is
  built into LKL and what LKL treats as the calling task's parent. A
  decision is needed only if the answer is not 0; either way this is TTR's
  anti-debugging check and belongs with the G8 conversation. See STATUS
  open question 6 (and the Phase 3 bench test listed there).
- `execve`, `wait4`, `clone(CLONE_VM|CLONE_VFORK)`: **Box64 itself** runs
  `sh -c lscpu` at start-up (popen) to name the CPU. Not possible under gx
  (C7); Phase 7 must make this fail cleanly or patch it out.
- `personality` (1 call, fails, Box64), `/dev/shm/box64_tmpcmdline` (Box64),
  `memfd_create` (1).
- `shmget/shmat/shmctl/shmdt`: SysV shared memory, from Mesa's X11 software
  presentation (MIT-SHM, `/SYSV00000000 (deleted)` mappings of 64 KiB and
  5.4 MiB). Replaced by the GL shim on the console (C3).
- 37 `clone` calls with `CLONE_VM|CLONE_THREAD|…|CLONE_SETTLS` (threads),
  plus the vfork above.
- `getpid` is called ~450 times per second.

### Memory

- `mmap` flag mixes seen: `RW PRIVATE|ANONYMOUS` (2181), file mappings
  `R/RX/RW PRIVATE|FIXED|DENYWRITE` (79 each: native libraries),
  **`RWX PRIVATE|ANONYMOUS` (48)**, `NONE …|NORESERVE` (21), stacks
  (`MAP_STACK` 30, `MAP_GROWSDOWN` 20), `MAP_SHARED` 5.
  **No `MAP_32BIT`.**
- `mprotect` to `PROT_READ|PROT_EXEC` 9,425 times, `PROT_READ` 2,318,
  `PROT_READ|PROT_WRITE` 1,076 — the dynarec's code-cache handling.
- Executable anonymous memory at the title screen: dynarec run 41 `rwxp`
  mappings (32.5 MiB) and 31 anonymous `r-xp`; interpreter run 18 `rwxp`
  pages (4 KiB each at 0x30000000…, Box64's bridges) and **no anonymous
  executable memory from the guest**. So up to the title screen the engine
  creates no x86 code at run time (no thunks/closures/JIT). In-game:
  pending the human run.

### Signals

- Host handlers installed (`/proc/<pid>/status`): `SigCgt
  000000010000046a` = SIGINT, SIGILL, SIGABRT, SIGBUS, SIGSEGV and signal 33
  (strace's `SIGRT_1`, used inside glibc); `SigIgn 0000000000011004` = SIGQUIT, SIGPIPE, SIGCHLD; `SigBlk
  0000000008001000` = SIGPIPE, SIGWINCH. SIGSEGV/SIGBUS/SIGILL/SIGABRT are
  Box64's own; SIGINT follows the engine (`rt_sigaction(SIGINT, …)` is
  called 2,512 times in 75 s — re-installed continuously).
- Delivered during the run: only `SIGCHLD` (Box64's lscpu child) and our
  `SIGTERM`. **No SIGSEGV delivered** with the dynarec to the title screen.
  What matters if signals are absent (C1/C8): SIGINT handling (cosmetic),
  Box64's fault handlers (dynarec SMC detection, Phase 10).

### GL (Phase 8)

- Pipe: GLX (`glxGraphicsPipe`), window `glxGraphicsWindow`; contexts from
  `glXCreateNewContext`/`glXCreateContextAttribsARB` with FBConfigs; pbuffers
  and GLX pixmaps looked up. Statically imports 86 `gl*` (fixed-function
  calls such as `glAlphaFunc`, `glCallList` among them) and 14 `glX*`.
- **Works with Mesa capped at GL 1.5 and 2.1** at the title screen
  (`MESA_GL_VERSION_OVERRIDE`). The game's own `settings.json` has
  `video.enable-shaders: true`, `v-sync: true`, `fps-limit: -1`,
  `resolution: [1280, 720]`; whether in-game rendering degrades below 3.x is
  pending the human run.
- GL version string and extension list as the engine reads them could not be
  logged: Panda3D ignores outside PRC config (`PANDA_PRC_DIR`), and a GL call
  tracer needs `LD_PRELOAD`, which makes the engine exit.

### X11 and input

179 `libX11` imports (full list in the imports file), plus the dlopened
`libXcursor`, `libXi`, `libXrandr`, `libXxf86dga` (missing, tolerated).
`Unable to set window properties: !undecorated !fixed_size icon:…` at start
(Xvfb has no window manager). Window title `Toontown Rewritten`, class
`com.toontownrewritten.Launcher`.

### Audio (Phase 8)

26 OpenAL imports (`alBufferData`, `alSourceQueueBuffers`/`Unqueue`, …,
`alcOpenDevice`, `alcCreateContext`). Box64 **wraps** `libopenal.so.1` and
uses the native arm64 OpenAL Soft 1.19.1, not the bundled x86-64 copy.
Device (`ALSOFT_LOGLEVEL=3`): ALSA `default`, **stereo, float, 44,100 Hz,
1,023-frame period × 3**, 256 sources, 64 effect slots, HRTF off. OpenAL
Soft probed JACK and PulseAudio first (creating `/dev/shm/jack_db-*`,
`/tmp/pulse-*`).

### Files the engine writes

In its install directory (cwd): `settings.json` (opened for writing 84
times in 75 s), `logs/ttr-<date>_<time>_<n>.log`, `.crashreport` (empty),
`resources/` (directory). Elsewhere: `/tmp/.ttr_safe_mode_<pid>`, one
`tempfile` in `/tmp`. The placeholder cookie value was found in **none** of
the engine's output or written files in 12 runs (`placeholder-cookie-found-in.txt`).
The engine prints `Using gameServer from launcher: <TTR_GAMESERVER>`.
**The engine writes a login token to its own log.** When it logs in, the
engine's log line `Successful login: <token>` (in
`logs/ttr-<date>_<time>_<n>.log` in the install directory and on stdout)
carries a long server-issued token. It is not the play cookie, so the
cookie scrub missed it in the first human runs; it was redacted by hand
and `human_run.py` now scrubs it by pattern. On the console the install
directory is on the SD card (`sdmc:/switch/ttr-nx2/game/`), so this needs a
design decision under rule 4 (STATUS open question 9).
