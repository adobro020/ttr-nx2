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
| G8 | Public release acceptable to the TTR team's rules? | before Phase 12 (human) | open | — |

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
| fresh `git clone --recurse-submodules` + `make hello` → `build/hello.nro` with `NRO0` at 0x10 | **done locally** | clone of the local repository into the scratch area; `00000010: 4e52 4f30 …  NRO0…` |
| Same build passes in GitHub Actions | pending human | needs the GitHub repository (approval) |
| Dummy `TTREngine` commit rejected by hook and CI | hook **done**; CI pending human | hook output in the Phase 0 PR; CI after push |
| `TTR_PLAYCOOKIE=<value>` line rejected by hook and CI | hook **done**; CI pending human | as above |
| `docs/upstream-notes.md` lists hash + licence for every upstream; matches `git submodule status` | **done** | see `docs/upstream-notes.md` |
| `docs/dev-setup-macos.md` names every installed tool and version | **done** | |
| Repository is private (`gh repo view --json visibility`) | pending human | `gh` not logged in; repository not created |

No hardware is needed for Phase 0. Optional smoke test: copy
`build/hello.nro` to `sdmc:/switch/` and start it from hbmenu (not done).

## Environment notes

- Development Mac: Apple silicon, macOS 27.2.1. arm64 containers native;
  x86-64 containers via Rosetta (Colima `--vz-rosetta`).
- Container images built here: ounce-devkit ~3.0 GB, bench-arm64 ~1.0 GB,
  ref-amd64 ~0.7 GB. Each built in about a minute after base pulls.

## Open questions (for the human)

1. **Disk space.** The Mac has ~15–17 GB free; the plan budgets 40 GB (LKL
   build trees, rootfs images, Box64 builds, three container images).
   Phase 0 fits. Phases 3–4 likely will not. Free space or move the
   Colima VM disk to an external drive before Phase 3. `make doctor` warns
   below 40 GB and fails below 10 GB.
2. **GitHub plan and private repositories.** On a free personal account,
   branch protection (and rulesets) are not enforced on private
   repositories, and GitHub's arm64 Linux runners are free only for public
   repositories. Options: GitHub Pro / Team; keep "protected main" as
   convention plus required CI by habit; or a self-hosted arm64 runner
   (this Mac) for bench jobs later. Your decision.
3. **GitHub setup approval.** Not done, because each step is outward-facing:
   `gh auth login` (you), then `tools/github/setup-project.sh create labels
   milestones protect`. The repository is created `--private`.
4. **Launcher pin.** Pinned to release 4.0; `master` is 5 commits ahead
   (progress display and formatting). Stay on the release or move to
   `master`? Recommendation: stay on 4.0 until Phase 2's contract tests.
5. **Colima configuration changed.** The project folder was added to
   Colima's mounts and Colima was restarted with Rosetta; Docker's config
   gained the Homebrew plugin path. Backups end in `.bak-ttrnx2`.
