# Status

Last updated: 2026-11-24 (Phase 0).

## Feasibility gates

| Gate | Question | Decided in | State | Evidence |
|---|---|---|---|---|
| G1 | TTREngine loadable at an arbitrary high address (PIE, no low-4 GB dependence)? | Phase 2 | open | — |
| G2 | Unmodified TTREngine runs under stock Box64 on ARM64 Linux? | Phase 2 | open | — |
| G3 | Console gives enough memory, JIT regions, GL, sockets, keyboard applet? | Phase 1 | open | — |
| G4 | Python 3.12 with `cryptography` and `requests` runs on gx on the console? | Phase 4 | open | — |
| G5 | Box64 interpreter runs real x86-64 programs on gx with no signals? | Phase 7 | open | — |
| G6 | Staged-JIT dynarec passes Box64's tests and gives ≥ 10× the interpreter? | Phase 10 | open | — |
| G7 | Game playable at Phase 11 frame-rate targets? | Phase 11 | open | — |
| G8 | Public release acceptable to the TTR team's rules? | before Phase 12 (human) | open (partly decided) | 2026-11-24: the human chose to make the **repository public** now. Whether a public *release* is acceptable to the TTR team is still open and still needed before Phase 12. |

## Phases

| Phase | Title | State | Notes |
|---|---|---|---|
| 0 | Workspace, toolchain and repository | **in progress** — local work done; GitHub steps await the human | see below |
| 1 | Hardware probes (G3) | not started | |
| 2 | Reference baselines (G1, G2) | not started | do early: G1 can end the project |
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
| `make doctor` exits 0 on this Mac | **done** | exit 0, "all requirements met, 1 warning(s)" (disk); output in the Phase 0 PR |
| fresh `git clone --recurse-submodules` + `make hello` → `build/hello.nro` with `NRO0` at 0x10 | **done locally** | clone of this repository (submodules fetched from GitHub) into `build/fresh-clone`, devkit image rebuilt with `--no-cache`; `00000010: 4e52 4f30 0000 0000 0030 0400 0000 0000  NRO0.....0......`; NRO SHA-256 `bac21a921412427f6f331e4551315094399fa28efe6ca873ef1638fdabb8b2ad`, identical to the first build |
| Same build passes in GitHub Actions | pending | repository exists; CI runs on a pull request into `main` (not opened yet) |
| Dummy `TTREngine` commit rejected by hook and CI | hook **done**; CI checks **done locally**; CI run pending human | throwaway branch (deleted): hook `FAIL game-file: TTREngine`; after `--no-verify`, `check.py --history HEAD` exit 1. Needs a CI run after push |
| `TTR_PLAYCOOKIE=<value>` line rejected by hook and CI | hook **done**; CI checks **done locally**; CI run pending human | hook `FAIL play-cookie: demo-cookie.env:1`; after `--no-verify`, history check and `gitleaks git` ("leaks found: 1") exit 1 |
| `docs/upstream-notes.md` lists hash + licence for every upstream; matches `git submodule status` | **done** | `af80b26…` launcher (4.0), `2f130fa…` box64 (v0.4.4), `8652bc7…` chromium-nx (v0.2.0) in both |
| `docs/dev-setup-macos.md` names every installed tool and version | **done** | |
| Repository is private (`gh repo view --json visibility`) | superseded | the human decided on 2026-11-24 to make it public (G8). https://github.com/adobro020/ttr-nx2 → `{"defaultBranchRef":{"name":"main"},"visibility":"PUBLIC"}`; labels and 13 milestones created |

No hardware is needed for Phase 0. Optional smoke test: copy
`build/hello.nro` to `sdmc:/switch/` and start it from hbmenu (not done).

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
5. **Colima configuration changed.** The project folder was added to
   Colima's mounts and Colima was restarted with Rosetta; Docker's config
   gained the Homebrew plugin path. Backups end in `.bak-ttrnx2`.
