# 0004 — Launcher contract tests: unmodified modules, fake API behind a socket redirect

Date: 2026-11-24. Status: accepted (Phase 2).

## Context

Phase 5's adapter drives the unmodified launcher (rule 3) from a GUI. Before
writing it we need an executable statement of what the launcher does: its
prompts, network calls, files and the game launch. Tests must never reach
TTR's servers (rule 5) and must not write into the launcher submodule.

## Options

1. Mock `requests` (e.g. `responses`, or patching `requests.post`). Simple, but
   skips TLS, sessions and streaming, and the patcher calls `requests.get`,
   `Session.get` and `requests.post` in different places.
2. Edit the launcher's URLs. Violates rule 3.
3. A real local HTTPS server (`tools/fake_ttr_api/`) with a throwaway CA, and
   a redirect at `urllib3.util.connection.create_connection` that maps the
   TTR host names to it and refuses every other destination. Terminal I/O is
   scripted by replacing `builtins.input` and `pwinput.pwinput`;
   `helper.get_launcher_path` points at a temporary directory; the launch is
   recorded by replacing `subprocess.Popen`/`run`.

## Decision

Option 3. TLS verification stays on (`REQUESTS_CA_BUNDLE` = test CA), so the
same code paths run as against TTR. The fake implements `login.md`
(api-doc `e18126c`) plus what the launcher requires beyond it (a
`queueToken` in every delayed response). The suite moves `make test` from
`unittest` to `pytest` (which also runs the existing unittest cases); the
launcher's packages and pytest are pinned in `tests/requirements.txt` and
installed into `.venv` by `make venv`. `make test` ends by checking that the
launcher submodule's `git status` is clean.

## Consequences

- Any destination the fake does not know raises `BlockedConnection`: a test
  cannot leak a request to TTR.
- The same fake serves Phase 5's adapter tests and the Phase 6 GUI tests.
- Two upstream quirks are pinned by tests (unreachable "Could not decode"
  branch; the mirror-removal race), see `docs/recon/launcher-contract.md`.
- `tests/requirements.txt` has a copy in `docker/bench-arm64/` (the image's
  build context); `make lint` fails if they differ.
