# Phase 12 — Packaging, documentation and release

Read `CLAUDE.md`, `docs/ARCHITECTURE.md` and `docs/STATUS.md` first.
Depends on Phase 11 (or on a decision to ship a labelled technical demo).
Gate **G8** belongs to the human and must be settled before anything is made
public.

## Goal

A tagged, reproducible release that a stranger can install from the README
alone, with every licence obligation met and nothing in it that belongs to
someone else.

## Before any public step

Prepare, for the human to act on:

- a short summary of what the project does and does not do, for them to send
  to the Toontown Rewritten team or check against TTR's current terms;
- the non-affiliation and "unofficial" wording used in the app, README and
  release notes;
- a list of every name and mark used and where.

The repository and releases stay private until the human says otherwise.

## Work

1. **Release contents**: `ttr-nx2.zip` unpacking to
   `switch/ttr-nx2/ttr-nx2.nro`, `rootfs.ext4` (or a first-run download of it
   verified by SHA-256, if size requires), `licenses/`, `README.txt`. No game
   files, no settings, no logs. NRO metadata: name with "(unofficial)",
   author, version, original icon.
2. **Reproducible release build**: `make release` in containers from a clean
   tag produces the same SHA-256 on the Mac and in CI. A GitHub Actions
   workflow builds on tag, attaches the zip, `SHA256SUMS`, and a source
   bundle or exact instructions satisfying GPL-2.0 for gx, LKL and any other
   copyleft part: pinned commits, patch series, kernel library config, and
   the Debian package list with source references for the rootfs.
3. **`THIRD_PARTY.md` and `licenses/`**: every component in the NRO and the
   rootfs with name, version, licence and source location. Generated from
   the build, checked in CI.
4. **Security review** of the whole project (use `/security-review` and your
   own reading). Threat model in `docs/security.md`: a lost or copied SD
   card; other homebrew on the same console; a hostile network; a tampered
   rootfs or update. Verify: TLS certificate validation is on everywhere;
   stored credentials are encrypted with a user secret; the redaction filter
   covers every sink; file access is confined to the app's folder; the debug
   redirect is absent from release builds; the rootfs hash is checked at
   start.
5. **Update check** (optional, off by default): compares the installed
   version with the latest GitHub release and shows a notice; downloads are
   verified by hash; no telemetry.
6. **User documentation** in `docs/user/` and the README: requirements
   (console with kaiHEN at a supported version, SD card space, Wi-Fi);
   install; first run; controls; settings; troubleshooting by symptom; how
   to produce a redacted report; uninstall; privacy (what is stored and
   where); risks stated plainly (kaiHEN's own brick warning, possible loss of
   Nintendo online services on a modified console, firmware updates, and
   that TTR may not support this way of playing).
7. **Contributor documentation**: `CONTRIBUTING.md`, the Mac setup guide
   from Phase 0 brought up to date, how to run each test tier, how to bump
   each upstream, the hardware test protocol, a code of conduct.
8. **Clean-room install test**: on a freshly formatted SD card, the human
   follows the README only. Fix the README wherever they had to guess.
9. **Listing** (human decision): prepare the metadata for the Switch 2
   homebrew list or package repository used by the community at the time.
10. **Project hygiene**: close or re-label every open issue; a `ROADMAP.md`
    of what was left out; `CHANGELOG.md`; version `1.0.0` or `0.x` according
    to which gates passed.

## Deliverables

Release workflow and artifacts, licence inventory, security document, user
and contributor documentation, clean-install report, roadmap and changelog.

## Acceptance criteria

- [ ] `make release` at the tag gives the same `SHA256SUMS` locally and in
      CI; link the run.
- [ ] Automated scan of the zip and the rootfs: no TTR game files, no
      `launcher.json`, no logs, no file matching the secret patterns.
- [ ] `THIRD_PARTY.md` lists every shared object and Python package present
      in the rootfs (CI compares the lists).
- [ ] Every item in the security checklist above has a test or a code
      reference beside it in `docs/security.md`; findings from the review are
      fixed or filed with severity.
- [ ] The asset audit from Phase 6 is repeated for the final NRO: icon,
      fonts, images and sounds all original or openly licensed, with sources.
- [ ] The human completed the clean-room install using only the README and
      reached the game; their notes are in `docs/hardware/`.
- [ ] `docs/STATUS.md` shows every gate's final state, and the release notes
      state honestly what works, what does not, and the measured performance.
- [ ] Nothing was made public without the human's explicit instruction.

## Hardware

The clean-room install: one session.

## If blocked

- G8 is not cleared: finish everything else, keep the repository private,
  and stop.
- A dependency's licence cannot be satisfied in a binary release: replace
  the dependency or make it a first-run download from its own source.
