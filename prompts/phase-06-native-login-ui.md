# Phase 6 — Native graphical login interface

Read `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/STATUS.md` and
`docs/protocol.md` first. Depends on Phase 5.

## Goal

A controller-and-touch login application, drawn natively on the console,
that is the host side of the adapter protocol: accounts, login, tokens,
queue, download progress, settings, errors, and a clean handover of the
screen to the game.

## Design constraints

- Native code in `host/gui/`, built with libounce. Use the SDL2 portlib if it
  builds unchanged under the devkit (ounce-devkit says it does; verify), with
  rendering through OunceVK's GLES. Record the choice of drawing and widget
  approach in an ADR. Keep dependencies few and permissively licensed.
- Text entry uses the system software keyboard, in password mode for every
  secret. Secrets are never drawn, never kept after being sent, and never
  logged.
- Original visual design. No Toontown, Disney or Nintendo artwork, logos,
  characters, fonts or sounds. Bundle an openly licensed font.
- Everything reachable with D-pad, A and B alone, and with touch alone.
  Legible in handheld mode: body text at least 28 px on the 1080p screen.
- The same UI code builds on macOS against SDL2 with a mock bridge, so
  screens can be developed and screenshot-tested without the console.

## Work

1. **Screen inventory and flow** in `docs/ui.md`, derived from the protocol,
   before code: first-run notice (unofficial, unaffiliated; what is stored
   on the SD card; console and account risks; requires acceptance once);
   home with account list and "Play"; add account; master password; login in
   progress with status lines; token entry showing the API's banner verbatim;
   queue with position and estimated wait; update with per-file and total
   progress, speed and free space; settings (stored accounts, master
   password change, game log on or off, storage use, licences, version);
   links shown as text with a QR code (there is no browser); error dialogs
   that show upstream's message; "starting game".
2. **UI toolkit**: focus navigation, lists, buttons, dialogs, progress bars,
   text wrapping, a QR encoder, a frame-time counter, scaling for 720p and
   1080p, light and dark following the console setting.
3. **Bridge**: the GUI runs on the main thread at display refresh; the Python
   guest runs on runtime threads; protocol messages cross through lock-free
   or mutex-guarded queues. The UI never blocks on the guest, and shows a
   spinner with the last status after 300 ms without a message.
4. **Lifecycle**: HOME, sleep and wake, dock and undock are handled without
   losing state; a network drop surfaces upstream's own error and returns to
   the home screen; B cancels any prompt.
5. **Handover**: on `handoff`, show "starting game", release fonts and
   textures, destroy the GL context and window surface, report freed memory,
   then give the guest the go-ahead. After that the GUI code does not run
   again in this process.
6. **Mac mock build** (`make gui-mac`) with scripted scenarios that render
   every screen and write PNGs; golden-image tests in CI with a small
   tolerance.
7. **Accessibility and wording pass**: plain language, no jargon, consistent
   button hints, colour contrast at least 4.5:1 for text.

## Deliverables

`host/gui/`, `docs/ui.md`, ADR, mock build and golden images, the integrated
NRO, `docs/hardware/phase-06-checklist.md` with a photo slot per screen.

## Acceptance criteria

- [ ] `make gui-mac` renders every screen in `docs/ui.md`; golden-image tests
      pass in CI; the PNGs are attached to the PR.
- [ ] Each protocol message type has a UI test that sends it through the mock
      bridge and asserts the resulting screen state.
- [ ] Automated check: no secret prompt answer appears in any UI log, and the
      software keyboard is invoked in password mode for every `secret` prompt.
- [ ] Asset audit in the PR: every image, font and sound listed with its
      origin and licence; nothing derived from third-party game art.
- [ ] Hardware (pending human until logged), against the fake server:
  - [ ] complete login-to-handoff flow using only the controller;
  - [ ] the same using only touch;
  - [ ] token prompt, queue and each error dialog seen and photographed;
  - [ ] cancelling the software keyboard returns to the previous screen;
  - [ ] during a 200 MB download the 95th-percentile frame time is under
        20 ms (from the frame-time log) and input stays responsive;
  - [ ] sleep and wake during login returns to a usable screen;
  - [ ] the log shows the GL context destroyed and memory released before
        the stub engine starts.
- [ ] The human signs off the checklist in `docs/hardware/`.

## Hardware

One session, about 30 minutes, following the checklist: fake server on the
Mac, both handheld and docked.

## If blocked

- SDL2 does not work under kaiHEN as expected: draw directly with EGL and
  GLES and read input through libounce; keep the toolkit layer unchanged.
- The software keyboard is unavailable in a game's process: build an
  on-screen keyboard in the toolkit, with password masking.
