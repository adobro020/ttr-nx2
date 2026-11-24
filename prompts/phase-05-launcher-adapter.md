# Phase 5 — Launcher adapter (headless)

Read `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/STATUS.md` and
`docs/recon/launcher-contract.md` first. Depends on Phases 2 and 4.

## Goal

The unmodified Simple TTR Launcher runs as a guest and is driven entirely
through a machine protocol: every prompt, status line, progress update and
the final game launch crosses that protocol instead of a terminal.

## Design constraints

- `third_party/Simple-TTR-Launcher` stays byte-identical. Do not import
  `main.py` (it runs the text menu at import). Use `launcher.Launcher`,
  `patcher`, `encrypt` and `helper` as they are.
- All adaptation is runtime substitution, installed before the launcher
  modules are imported, and limited to the call sites listed in
  `launcher-contract.md`.
- The adapter must run unchanged in three places: macOS CPython (unit tests),
  the gx bench, and the console.

## Work

1. **Protocol** (`docs/protocol.md`, version 1): newline-delimited JSON over
   two host-provided descriptors. Guest to host: `hello`, `prompt` (id, kind
   `text` | `secret` | `choice` | `confirm`, label, bounds), `status` (text,
   severity), `progress` (stage, done, total, file), `accounts`, `settings`,
   `link` (url), `handoff`, `fatal`. Host to guest: `answer` (id, value or
   cancel), `command` (`play`, `add_account`, `change_password`,
   `remove_account`, `get_settings`, `set_setting`, `quit`). Text from the
   API (banners) is passed through verbatim.
2. **Shims** in `guest/adapter/`:
   - `builtins.input` and `pwinput.pwinput` → `prompt` and wait for `answer`;
   - `helper.confirm` → a `choice` prompt with the same bounds and return type;
   - `helper.clear` → nothing (it shells out, which gx cannot do);
   - `helper.quit_launcher` → `fatal`, then exit;
   - `print` → `status`, keeping upstream's wording, never parsed for logic;
   - `tqdm` and `thread_map` as used by `patcher` → `progress` events, with
     the worker count capped to a value that suits the SD card and the NAT;
   - `webbrowser.open` → `link`;
   - `helper.get_launcher_path` → the writable `data/` mount, so
     `launcher.json` lives on the SD card and not in the read-only image;
   - the install directory setting fixed to the `game/` mount;
   - `subprocess.Popen` and `subprocess.run` in `launcher` → validate the
     requested binary is `TTREngine` inside the install directory, send
     `handoff`, wait for the host's go-ahead, then
     `os.execve(<box64>, [<box64>, <engine>], env)` with the working
     directory set as upstream does. The exec target is configurable so tests
     can exec a stub.
3. **Credential policy** (architecture decision 8): on first run, write
   settings so stored accounts are encrypted with a master password, using
   either upstream's own Argon2id and Fernet path or the Phase 4 keyring
   backend. Choose one in an ADR. The UI must never offer plaintext storage.
4. **Secret hygiene**: answers to `secret` prompts and every value the login
   API returns under `cookie`, `responseToken`, `queueToken` are registered
   with the redaction filter the moment they exist. `handoff` carries no
   secret. The engine's environment is the only place the cookie goes.
5. **Test endpoint redirection**: a transport-level redirect to the fake
   server, compiled in only for debug builds and enabled only by an explicit
   flag shown in the log's first line. Release builds cannot be redirected.
6. **Headless driver** (`tools/drive.py`): scripts the host side of the
   protocol for tests, on macOS and over the bench's descriptors.
7. **Upstream drift check** (`tools/check_sttrl_contract.py`): verifies at
   the pinned commit that each substituted name exists with the expected
   signature; CI runs it, and it is the first thing to run when bumping the
   submodule.
8. **Stub engine**: a small aarch64 guest program that reports whether
   `TTR_GAMESERVER` and `TTR_PLAYCOOKIE` are present (never their values),
   its working directory and its argument list.

## Deliverables

Adapter package, protocol document, driver, drift check, stub engine, tests,
ADR on credential storage, `docs/hardware/phase-05-checklist.md`.

## Acceptance criteria

- [ ] CI check: the launcher submodule tree hash equals the pinned one.
- [ ] The Phase 2 contract scenarios all pass through the adapter and driver
      in three environments: macOS, `make bench`, `make test-nx2like`. Show
      three summaries. Scenarios: success; wrong password banner; ToonGuard
      or 2FA token accepted on the second try; queue with decreasing
      position; network down then recovered; fresh install; bsdiff update;
      hash mismatch; disk full; user cancels at each prompt.
- [ ] Account management scenarios pass: add, change password, remove, wrong
      master password three times.
- [ ] After the full suite, a search of every log and every file under the
      test `data/`, `cache/` and `logs/` for the fixture password, tokens and
      cookie finds nothing (automated, part of the suite).
- [ ] Handoff test: the stub engine starts by `execve`, reports both
      variables present and the working directory equal to the install
      directory; the Python interpreter's threads and memory are gone
      (runtime counters from Phase 3).
- [ ] A release-configuration build ignores the redirect flag (test).
- [ ] The drift check passes at the pinned commit and fails when pointed at
      a copy with one substituted function renamed (test).
- [ ] Hardware (pending human until logged): the scripted fake-server flow,
      from login to stub-engine handoff, passes on the console over Wi-Fi,
      including a 200 MB fixture download to the SD card with its hash
      verified.

## Hardware

Console and Mac on the same network; the Mac runs the fake server. The
console build runs the scripted driver internally and logs each step.

## If blocked

- An upstream call site cannot be substituted without editing the source:
  stop and propose the smallest upstream pull request instead of a local edit.
- Patching speed on the SD card is poor: measure, then tune worker count and
  buffer sizes in the shim; do not change upstream's verification steps.
