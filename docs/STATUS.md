# Status

Last updated: 2026-11-24 (Phase 2).

## Feasibility gates

| Gate | Question | Decided in | State | Evidence |
|---|---|---|---|---|
| G1 | TTREngine loadable at an arbitrary high address (PIE, no low-4 GB dependence)? | Phase 2 | **passed** (2026-11-24) | `readelf -h`: `Type: DYN (Position-Independent Executable file)`; `readelf -l`: first `LOAD` at `0x0000000000000000`, `FLAGS_1: PIE`, relocations only `RELATIVE`/`GLOB_DAT`/`64`/`JUMP_SLOT`, no `TEXTREL`; no `MAP_32BIT` in the start-up syscall trace; stock Box64 maps it at `0x100000000` and it runs. `docs/recon/engine-91bff107.md` §2 |
| G2 | Unmodified TTREngine runs under stock Box64 on ARM64 Linux? | Phase 2 | **passed to the title screen; logged-in part pending human run** | offline (network off, placeholder cookie): window, GLX context, OpenAL, fonts, title screen at ~68 fps (llvmpipe) with the dynarec. Toon selection needs the human's login: `docs/recon/human-run.md`. `docs/recon/engine-91bff107.md` §3–4 |
| G3 | Console gives enough memory, JIT regions, GL, sockets, keyboard applet? | Phase 1 | open | — |
| G4 | Python 3.12 with `cryptography` and `requests` runs on gx on the console? | Phase 4 | open | — |
| G5 | Box64 interpreter runs real x86-64 programs on gx with no signals? | Phase 7 | open | — |
| G6 | Staged-JIT dynarec passes Box64's tests and gives ≥ 10× the interpreter? | Phase 10 | open | — |
| G7 | Game playable at Phase 11 frame-rate targets? | Phase 11 | open | — |
| G8 | Public release acceptable to the TTR team's rules? | before Phase 12 (human) | open (partly decided) | 2026-11-24: the human chose to make the **repository public** now. Whether a public *release* is acceptable to the TTR team is still open and still needed before Phase 12. |

## Phases

| Phase | Title | State | Notes |
|---|---|---|---|
| 0 | Workspace, toolchain and repository | **done** (2026-11-24) | merged in adobro020/ttr-nx2#1; see below |
| 1 | Hardware probes (G3) | not started | |
| 2 | Reference baselines (G1, G2) | **done offline**; human run pending | see below |
| 3 | gx runtime | not started | |
| 4 | Python guest (G4) | not started | |
| 5 | Launcher adapter | not started | |
| 6 | Native login UI | not started | |
| 7 | Box64 interpreter (G5) | not started | |
| 8 | Display, audio, input | not started | |
| 9 | First boot | not started | |
| 10 | Staged-JIT dynarec (G6) | not started | |
| 11 | Playable (G7) | not started | |
| 12 | Release (G8) | not started | |

### Phase 0 acceptance

| Criterion | State | Evidence |
|---|---|---|
| `make doctor` exits 0 on this Mac | **done** | exit 0, "all requirements met, 1 warning(s)" (disk); output in adobro020/ttr-nx2#1 |
| fresh `git clone --recurse-submodules` + `make hello` → `build/hello.nro` with `NRO0` at 0x10 | **done locally** | clone of this repository (submodules fetched from GitHub) into `build/fresh-clone`, devkit image rebuilt with `--no-cache`; `00000010: 4e52 4f30 0000 0000 0030 0400 0000 0000  NRO0.....0......`; NRO SHA-256 `bac21a921412427f6f331e4551315094399fa28efe6ca873ef1638fdabb8b2ad`, identical to the first build |
| Same build passes in GitHub Actions | **done** | PR #1 run https://github.com/adobro020/ttr-nx2/actions/runs/45339233652 (both jobs pass; `hello-nro` artifact uploaded); `main` after merge: https://github.com/adobro020/ttr-nx2/actions/runs/45340795984 (success) |
| Dummy `TTREngine` commit rejected by hook and CI | **done** | hook, on a local throwaway branch (deleted): `FAIL game-file: TTREngine`. CI: draft adobro020/ttr-nx2#2 (committed with `--no-verify`), job https://github.com/adobro020/ttr-nx2/actions/runs/45341621350/job/138266366932 failed at "Guard rails (tree at HEAD)": `guardrails: FAIL game-file: TTREngine (index) matches a TTR game file pattern`. PR closed unmerged, branch deleted |
| `TTR_PLAYCOOKIE=<value>` line rejected by hook and CI | **done** | hook: `FAIL play-cookie: demo-cookie.env:1`. CI: draft adobro020/ttr-nx2#3 (`--no-verify`), job https://github.com/adobro020/ttr-nx2/actions/runs/45341619156/job/138266359494 failed at "Guard rails (tree at HEAD)": `guardrails: FAIL play-cookie: demo-cookie.env:1 (index) assigns a value to TTR_PLAYCOOKIE` (value not printed). PR closed unmerged, branch deleted. The dummy value stays visible in the closed PR's history; it was never a real cookie |
| `docs/upstream-notes.md` lists hash + licence for every upstream; matches `git submodule status` | **done** | `af80b26…` launcher (4.0), `2f130fa…` box64 (v0.4.4), `8652bc7…` chromium-nx (v0.2.0) in both |
| `docs/dev-setup-macos.md` names every installed tool and version | **done** | |
| Repository is private (`gh repo view --json visibility`) | superseded | the human decided on 2026-11-24 to make it public (G8). https://github.com/adobro020/ttr-nx2 → `{"defaultBranchRef":{"name":"main"},"visibility":"PUBLIC"}`; labels and 13 milestones created |

Branch protection on `main` (2026-11-24, at the human's request): both CI
jobs required, branch must be up to date, force-pushes and deletion blocked,
admins can override (`enforce_admins` off). Read back with
`gh api repos/adobro020/ttr-nx2/branches/main/protection`. If a CI job is
renamed or a required job added, update `tools/github/setup-project.sh
protect` and re-run it in the same PR.

No hardware is needed for Phase 0. Optional smoke test: copy
`build/hello.nro` to `sdmc:/switch/` and start it from hbmenu (not done).

### Phase 2 acceptance

| Criterion | State | Evidence |
|---|---|---|
| `make test` runs the launcher contract suite on macOS; all step-2 scenarios pass | **done** | `45 passed, 7 subtests passed in 19.32s` (tests/unit + tests/launcher, Python 3.12.x on macOS). Scenarios: success with fresh install and launch; failure with and without banner; partial → partial → success; partial rejected; queue 3 → 2 → 1 → success; queue failure; login HTTP errors with retries; network failure (HTTP 500 and refused); stored accounts with keyring off and master password (Argon2id + Fernet round trip, wrong password ×3, account selection); keyring path; disable encryption; incremental bsdiff update; up-to-date; unknown local version; Linux file selection; compressed / decompressed / post-patch hash mismatch; mirror failover; all mirrors down; mirror list down; manifest retry; non-JSON manifest; declined install dir; `Popen` and `run` launch arguments and environment |
| `git status` in `third_party/Simple-TTR-Launcher` clean after the run | **done** | `make test` ends with `test: third_party/Simple-TTR-Launcher clean after the run`; `git -C third_party/Simple-TTR-Launcher status --porcelain` prints nothing |
| `launcher-contract.md` lists every `input`, `pwinput`, print-prompt, `confirm`, `clear`, `webbrowser`, `tqdm`, `subprocess` call site with file and line | **done** | `docs/recon/launcher-contract.md` §2–3, at `af80b26` |
| Recon answers ELF type, load addresses, needed libraries, imported symbol counts per library, with output quoted | **done** | `docs/recon/engine-91bff107.md` §2–3; names in `engine-91bff107-imports.txt` |
| G1 verdict with `readelf -h` / `readelf -l` lines | **done: passed** | engine doc §2 |
| Syscall, signal, GL and audio facts from a run that reached the engine's own window | **done offline; in-game items pending human** | engine doc §4–5 (runs reached the title screen) |
| G2 verdict or "pending human run" with the run sheet ready | **passed to the title screen; logged-in part pending human** | `docs/recon/human-run.md`, `make human-run` |
| CI game-file check passes: nothing from `ref/` tracked | **done locally** | `python3 tools/guardrails/check.py --all` → `guardrails: ok`; `git check-ignore -v ref/game/TTREngine` → `.gitignore:16:ref/`. CI run: on the PR |

Pending human (Phase 2): the logged-in runs in `docs/recon/human-run.md`
(dynarec with syscall counts, then interpreter only) to the toon selection
screen.

Deviations from the phase prompt, with reasons:

- The recon document is `docs/recon/engine-91bff107.md`, not
  `ttrengine-<version>.md`: the guard rails reject file names starting with
  `ttrengine` (ADR 0005).
- `make test` now uses pytest in a `.venv` (ADR 0004).
- Syscalls were collected with strace answering `PTRACE_TRACEME` with 0
  (strace fault injection, offline). Without it the engine exits under any
  tracer; attaching later is impossible (engine doc §5).
- GL version string/extension list in use could not be logged (engine doc §5,
  GL); replaced by the 174 entry points the engine resolves and runs with GL
  capped at 1.5 and 2.1.

## Environment notes

- Development Mac: Apple silicon, macOS 27.2.1. arm64 containers native;
  x86-64 containers via Rosetta (Colima `--vz-rosetta`).
- Container images built here: ounce-devkit ~3.0 GB, bench-arm64 ~1.0 GB,
  ref-amd64 ~0.7 GB. Each built in about a minute after base pulls.

## Open questions (for the human)

1. **Disk space.** The Mac has ~14–17 GB free (14 GB after Phase 0's images); the plan budgets 40 GB (LKL
   build trees, rootfs images, Box64 builds, three container images).
   Phase 0 fits. Phases 3–4 likely will not. Free space or move the
   Colima VM disk to an external drive before Phase 3. `make doctor` warns
   below 40 GB and fails below 10 GB.
   *Phase 2 update:* 13 GB free at the end of Phase 2 (24 GB at its start).
   The Colima disk file now holds 17 GB (images 10.2 GB, of which 2.4 GB are
   superseded bench images; build cache 4.9 GB). `docker image prune` and
   `docker builder prune` would reclaim some of it inside the VM, but the
   sparse disk file only shrinks on the Mac after `fstrim` in the VM. Not
   done: your call. Phase 3 will fail `make doctor` below 10 GB.
2. **Repository visibility (decided).** Public, by the human's decision on
   2026-11-24. On a public repository branch protection is enforced on the
   free plan and GitHub's arm64 runners are free, which settles the earlier
   plan question. Commits use a GitHub noreply author address. Labels and
   milestones requested; branch protection on `main` not yet requested.
3. **TTR team.** The repository being public does not answer whether TTR
   accepts a public release (G8). Contacting them before Phase 12 remains
   the human's call.
4. **Launcher pin.** Pinned to release 4.0; `master` is 5 commits ahead
   (progress display and formatting). Stay on the release or move to
   `master`? Recommendation: stay on 4.0 until Phase 2's contract tests.
   *Phase 2 update:* the contract suite now exists. `master` reformats
   every module and changes the progress display and download helper
   signatures; nothing in it is needed. Recommendation: stay on 4.0; re-run
   `make test` on any bump, and bump only when a release follows.
5. **Colima configuration changed.** The project folder was added to
   Colima's mounts and Colima was restarted with Rosetta; Docker's config
   gained the Homebrew plugin path. Backups end in `.bak-ttrnx2`.
6. **`PTRACE_TRACEME` on the console (new, Phase 2).** The engine calls
   `ptrace(PTRACE_TRACEME)` once at start-up and exits if it fails; on
   normal Linux the launcher becomes its tracer. gx has no ptrace, so gx (or
   Box64) must answer this call with success for the game to run at all.
   That is answering an anti-debugging check the TTR team put in the client.
   It changes nothing on disk and adds no debugging, but it belongs with the
   G8 question to the TTR team. Recommendation: implement it in gx as
   "PTRACE_TRACEME succeeds, no tracer exists" (the honest state of a
   process nobody traces), and mention it when contacting TTR.
7. **Human run.** `docs/recon/human-run.md`: two logins with your own
   account in the bench container (about 20 minutes). Closes G2.
8. **Colima stopped once on its own** during Phase 2 (between runs);
   `colima start --vz-rosetta` brought it back with no loss.
