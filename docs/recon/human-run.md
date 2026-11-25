# Human run sheet — TTREngine under stock Box64, logged in

Phase 2, step 8. For the human only: it uses your own TTR account, typed by
you at the launcher's own prompts. Nobody else (including Claude) sees or
handles the credentials. About 20 minutes.

What it gives the project: how the engine behaves from login to the **toon
selection screen** under stock Box64 on arm64 Linux, which the offline runs
cannot reach (they stop at the title screen), and the interpreter-only frame
cost there. Results close gate G2.

## What runs

`make human-run` starts the bench container (`docker/bench-arm64`) with
networking on and opens a virtual screen you watch over VNC on your Mac's
loopback (`localhost:5900`, not reachable from other machines, with a
throwaway password printed in Terminal). Inside it,
`tools/ref/human_run.py` runs the **unmodified** Simple TTR Launcher 4.0:

- account storage and the OS keyring are **off**: you type your username and
  password each run and nothing about the account is written to disk;
- the game is a copy of `ref/game/` inside the container (if TTR has
  updated since the files were fetched, the launcher's patcher updates the
  copy — that is the launcher's normal behaviour);
- the one change is how the game starts: `box64 TTREngine` instead of
  `TTREngine`, with logging, frame counting and memory sampling;
- when the game exits, every output file is searched for the play cookie
  and each occurrence is replaced with `[REDACTED-COOKIE]`; the count is
  printed, the value never is.

Network: the launcher talks to `www.toontownrewritten.com`, the CDN and
mirrors exactly as on any computer; the game talks to TTR's game server.
This is one normal login by you, as with the launcher on a desktop.

## Before you start

1. Colima is running (`colima status`; else `colima start --vz-rosetta`).
2. The fetched game files exist: `ls ref/game/TTREngine`.
3. Optional: free memory. The game uses about 0.6 GB; software rendering
   keeps 4–6 CPU cores busy.

## Steps

### Run 1 — dynarec (normal Box64)

1. In Terminal, in the project folder:

   ```bash
   make human-run MODE=dynarec STRACE=1
   ```

   (`STRACE=1` adds syscall **counts** only: no arguments, no environment.)
2. In Finder choose **Go → Connect to Server…**, enter
   `vnc://localhost:5900`, and connect. Screen Sharing asks for a password:
   use the one Terminal printed (`Screen Sharing password for this run: …`).
   It is new each run, only works on this Mac, and is **not** your TTR
   password. A black screen is normal until the game starts.
3. Back in Terminal, the launcher asks `Enter username:` and
   `Enter password:` (masked). If your account uses two-factor or ToonGuard,
   it shows TTR's message and asks `Enter token:`. If you are queued it
   prints your position and waits.
4. When the launcher prints `Login successful!` and `human-run: starting the
   engine`, the game appears in the VNC window. With dynarec it takes about
   15 s.
5. Press a key at the title screen, go to the **toon selection screen**, and
   **stay there for 60 seconds** without moving.
6. Quit the game from the toon selection screen (the game's own Quit button).
   Terminal prints `engine exited with status …` and
   `replaced the play cookie N time(s)`.

### Run 2 — interpreter only (no dynarec)

Same steps with:

```bash
make human-run MODE=interp
```

Expect it to be much slower (minutes to reach the toon selection screen, a
very low frame rate). Reaching the toon selection screen and waiting 60 s
there is enough; if it has not got there after 15 minutes, quit and note how
far it got.

## What to keep and send back

Each run writes to `build/human-run/<mode>/` (git-ignored, never committed):

| File | What it is |
|---|---|
| `engine.log` | Box64 and engine console output |
| `samples.txt` | every 5 s: threads, resident memory, peak memory, CPU time |
| `hud/fps` | frames per second, one value per second |
| `strace-count.txt` | syscall counts (run 1 only) |
| `game-files/` | the engine's own log and `settings.json` from the install directory |

Then:

1. **Check for the cookie yourself.** The script redacts it, but look:
   `grep -rIl -- "REDACTED-COOKIE" build/human-run` lists files where it was
   found (and replaced). If you ever see your cookie value or password
   anywhere, delete that file (`rm` it) and tell Claude which file it was,
   not what it contained.
2. Commit nothing from `build/`. Either paste `samples.txt`, `hud/fps`,
   `strace-count.txt` and the `engine.log` lines from `[BOX64]` into the
   chat, or tell Claude the runs are done and it will read them from
   `build/human-run/` on this Mac.
3. Note in words: which screen each run reached, roughly how it felt
   (smooth, slow, stutters), and anything odd (missing sound, black textures).

Delete the outputs when Claude has read them:

```bash
rm -r build/human-run
```

## Notes

- Logging in to TTR from a Linux container is the same as logging in from
  any Linux desktop with the same launcher. Two runs means two logins.
- If the VNC window stays black after `starting the engine`, wait 30 s
  (interpreter mode: several minutes). If Terminal shows
  `engine exited with status` straight away, send `engine.log`.
- Never run these steps with someone else's account, and do not share the
  output folder before checking it as in step 1.
