# Phase 8 — Display, audio and input for the engine

Read `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/STATUS.md`, the Phase 1
probe summary and the Phase 2 engine recon first. Depends on Phases 3 and 7.

## Goal

An x86-64 program that opens an X11 window with a GLX context, plays sound
and reads keyboard and mouse gets a working screen, speakers and controls on
the console, through shim libraries that Box64 treats as the native ones.

## How it fits

Box64 wraps calls to system libraries and forwards them to native aarch64
libraries of the same name. We supply those native libraries. Each exports
exactly what the engine imports (the lists are in the recon document) and
implements it by calling the host bridge.

## Decisions to make first (one ADR each, from evidence)

1. **OpenGL path.** If Phase 1 showed OunceVK offers a desktop OpenGL
   compatibility context covering what the recon says the engine uses, the GL
   shim forwards calls to the host one-to-one. Otherwise use a GL-to-GLES
   translator (gl4es, MIT) as the guest `libGL` over the host's GLES. Decide
   by running the Phase 2 GL trace's feature list against each.
2. **Audio path.** Follow the recon: if the engine uses OpenAL, ship the
   stock aarch64 OpenAL Soft and give it a small ALSA shim that feeds the
   host's audio output (Chromium NX's `guest/asound.c` is the precedent). If
   it uses something else, shim at the lowest library boundary that is
   openly documented.
3. **Default controls.** The game is keyboard and mouse. Read its default key
   bindings from its own options screen (ask the human) and design a default
   controller profile; store profiles as JSON on the SD card.

## Work

1. **`libX11` shim family** (`guest/shims/x11/`): `libX11` and whichever of
   `libXext`, `libXrandr`, `libXcursor`, `libXxf86vm`, `libXi` the recon
   lists. One display, one screen, one window that is the whole screen.
   Implement: display and window life cycle; atoms and the properties the
   engine sets; the event queue; key symbol and text lookup; pointer
   position, buttons, grab and warp (relative mouse movement); cursor
   show and hide; mode list with the console's modes. Anything else exported
   logs once by name and returns the documented failure value.
2. **GLX to EGL** in the GL shim: visual and config selection, context
   creation with the attributes the engine asks for, make-current per
   thread, swap with swap interval, extension strings limited to what works.
3. **GL forwarding**: hostcalls run on the calling guest thread with the
   context current there. Keep per-call overhead low (direct call through a
   table, no locking on the hot path). Add an optional call log and a frame
   capture to PNG for tests.
4. **Input service** in the host: gathers pad, touch, Joy-Con 2 mouse mode,
   USB keyboard and USB mouse; applies the profile; feeds X11 events. Touch
   acts as an absolute pointer with tap to click. A pad button opens the
   software keyboard and types the result as key events (for chat). HOME and
   sleep are handled by the host, not passed to the game.
5. **Audio service**: mixing format and buffer sizes from the recon;
   underrun counter in the log; clean stop on exit.
6. **Display modes**: render at 1280×720 or 1920×1080, chosen in a config
   file; handle dock and undock by reporting a mode change the way X11 would.
7. **Test programs**, x86-64, original code, run under Box64 on the bench
   (with Mesa in the container for the host side) and on the console:
   coloured triangle with fixed-function calls; textured, lit, depth-tested
   scene with vertex buffers; a GLSL shader test at the shading-language
   version the engine uses; render to texture; an input echo that draws
   received events; a tone and a streamed audio test; a combined "mini game
   loop" that reports frames per second and input latency.
8. **A closer rehearsal**, optional but recommended: a minimal program built
   with the open-source Panda3D engine for x86-64 Linux (procedural geometry,
   no third-party assets), run under Box64 through the shims. It exercises
   the same windowing and GL code paths family as the real engine without
   needing an account.

## Deliverables

Shim libraries, host input and audio services, three ADRs, test programs
with golden frames, controller profile format and default,
`docs/hardware/phase-08-checklist.md`.

## Acceptance criteria

- [ ] Symbol coverage report: every X11, GLX, GL and audio symbol in the
      recon's import list is exported by a shim; the "unimplemented, logged"
      set is listed and justified.
- [ ] `make bench` and `make test-nx2like`: every graphics test's captured
      frame matches its golden image within tolerance; the input echo test
      receives every scripted event in order; audio tests write the expected
      samples to the bench's file sink.
- [ ] No hostcall on the per-draw path takes a lock (code review note in the
      PR) and the mini game loop's hostcall overhead is reported per frame.
- [ ] Hardware (pending human until logged):
  - [ ] each graphics test shows the expected picture (photo and a frame
        capture file pulled from the SD card);
  - [ ] audio plays for five minutes with zero underruns in the log;
  - [ ] pad, touch, Joy-Con 2 mouse, USB keyboard and USB mouse each pass
        the echo test (or are recorded as unavailable on this console);
  - [ ] text typed through the software keyboard arrives as key events;
  - [ ] dock and undock while the mini game loop runs keeps rendering.
- [ ] The interpreter-mode frame rate of the mini game loop is recorded as
      the baseline for Phase 10.

## Hardware

About 30 minutes with the checklist; a USB keyboard and mouse if the human
has them.

## If blocked

- The host GL lacks a feature the engine needs: switch to the translator
  path, or implement the single missing feature in the shim, and record
  which.
- Zink or the Vulkan driver crashes on a call sequence (and the process dies
  silently): bisect with the call log on the bench against Mesa first, then
  with breadcrumbs on the console; report driver bugs to OunceVK with a
  minimal native reproducer.
