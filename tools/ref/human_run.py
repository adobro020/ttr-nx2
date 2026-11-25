#!/usr/bin/env python3.12
# SPDX-License-Identifier: GPL-2.0-only
"""The human's logged-in reference run (docs/recon/human-run.md).

Runs the **unmodified** launcher (``Launcher().prepare_login()``) inside
docker/bench-arm64. The human types their own username, password and any
token at the launcher's own prompts; this script never sees them except as
the launcher holds them in memory. Only three things are adapted from
outside, as Phase 5's adapter will do:

* ``helper.get_launcher_path`` points at a scratch directory inside the
  container, with account storage and the OS keyring off, so nothing about
  the account is written to disk;
* the install directory is a copy of ``ref/game`` inside the container;
* the final ``subprocess.Popen``/``run`` (launcher.py:284-288) starts
  ``box64 TTREngine`` instead, optionally under ``strace -f -c``, with Mesa's
  frame counter dumped to a file, and samples thread count, memory and CPU.

When the game exits, every output file is searched for the play cookie and
each occurrence is replaced with ``[REDACTED-COOKIE]`` (CLAUDE.md rule 4);
the number of replacements is printed, never the value. Output:
``build/human-run/<mode>/`` (git-ignored).
"""

from __future__ import annotations

import argparse
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER_DIR = ROOT / "third_party" / "Simple-TTR-Launcher"
STAGE = ROOT / "build" / "box64-bench" / "stage"
BOX64 = ROOT / "build" / "box64-bench" / "box64"
REDACTED = b"[REDACTED-COOKIE]"


def newest_engine_pid() -> int | None:
    """The newest process whose name is TTREngine, read from /proc."""
    best = None
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if (entry / "comm").read_text().strip() == "TTREngine":
                best = max(best or 0, int(entry.name))
        except OSError:
            continue
    return best


def sample(pid_holder: dict[str, int], out: Path, stop: threading.Event) -> None:
    clk = os.sysconf("SC_CLK_TCK")
    start = time.monotonic()
    with out.open("w") as f:
        f.write("t_s threads vmrss_kb vmhwm_kb utime_s stime_s\n")
        while not stop.wait(5):
            pid = pid_holder.get("engine")
            if not pid:
                continue
            try:
                # Not subprocess/pgrep: main() replaces subprocess.run with
                # start_engine, which made every sample fail in the first
                # human runs. Box64 renames its process to TTREngine.
                pid = newest_engine_pid() or pid
                status = Path(f"/proc/{pid}/status").read_text()
                stat = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
            except (OSError, ValueError):
                continue
            fields = dict(line.split(":", 1) for line in status.splitlines() if ":" in line)
            f.write(f"{time.monotonic() - start:.0f} {fields['Threads'].strip()} "
                    f"{fields['VmRSS'].split()[0]} {fields['VmHWM'].split()[0]} "
                    f"{int(stat[11]) / clk:.2f} {int(stat[12]) / clk:.2f}\n")
            f.flush()


# The engine's own log prints a login token after "Successful login: "
# (seen in the first human runs). It is not the play cookie, so it is
# scrubbed by pattern (CLAUDE.md rule 4).
LOGIN_TOKEN_RE = re.compile(rb"(Successful login: )(?!\[REDACTED)\S+")
REDACTED_TOKEN = rb"\1[REDACTED-LOGIN-TOKEN]"


def scrub(directory: Path, secret: str) -> int:
    """Redact the cookie and the engine's login token under ``directory``.

    Returns the number of replacements made.
    """
    needle = secret.encode() if secret else b""
    total = 0
    for path in directory.rglob("*"):
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            n = data.count(needle) if needle else 0
            if n:
                data = data.replace(needle, REDACTED)
            data, k = LOGIN_TOKEN_RE.subn(REDACTED_TOKEN, data)
            if n or k:
                path.write_bytes(data)
                total += n + k
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", choices=["dynarec", "interp"], default="dynarec")
    parser.add_argument("--strace", action="store_true",
                        help="run the engine under strace -f -c (syscall counts only)")
    args = parser.parse_args()
    if args.strace:
        # strace traces the engine, so its one ptrace(PTRACE_TRACEME) fails
        # and it exits with status 1 (observed in the first human run).
        # The offline runs answered that call with strace fault injection;
        # doing that while logged in to TTR's live servers would mean
        # defeating their anti-debugging check, which is the open decision
        # in docs/STATUS.md question 6. So logged-in runs never use strace.
        print("human-run: --strace is not available for logged-in runs: the "
              "engine refuses to run under a tracer (docs/recon/human-run.md)",
              file=sys.stderr)
        return 2

    out = ROOT / "build" / "human-run" / args.mode
    shutil.rmtree(out, ignore_errors=True)
    (out / "hud").mkdir(parents=True)
    home = Path(tempfile.mkdtemp(prefix="launcher-home-"))
    game = Path(tempfile.mkdtemp(prefix="game-")) / "game"
    shutil.copytree(ROOT / "ref" / "game", game)
    (home / "launcher.json").write_text(json.dumps({
        "accounts": {},
        "launcher": {"ttr-dir": str(game), "use-stored-accounts": False,
                     "use-password-encryption": False, "display-logging": False,
                     "use-os-keyring": False}}))

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(LAUNCHER_DIR))
    sys.argv = ["main.py"]
    import helper    # upstream, unmodified
    import launcher  # upstream, unmodified
    helper.get_launcher_path = lambda: str(home)
    os.chdir(home)

    pid_holder: dict[str, int] = {}
    stop = threading.Event()
    real_popen = subprocess.Popen

    def start_engine(*_a: object, **kw: object) -> subprocess.CompletedProcess[bytes]:
        process = str(kw["args"])
        env = dict(os.environ)
        env.update({
            "BOX64_LOG": "1",
            "BOX64_DYNAREC": "1" if args.mode == "dynarec" else "0",
            "BOX64_RCFILE": str(STAGE / "etc" / "box64.box64rc"),
            "BOX64_LD_LIBRARY_PATH": str(STAGE / "usr/lib/box64-x86_64-linux-gnu"),
            "LIBGL_ALWAYS_SOFTWARE": "1", "GALLIUM_DRIVER": "llvmpipe",
            "GALLIUM_HUD": "fps", "GALLIUM_HUD_PERIOD": "1",
            "GALLIUM_HUD_DUMP_DIR": str(out / "hud"),
        })
        cmd = [str(BOX64), process]
        if args.strace:
            cmd = ["strace", "-f", "-c", "-S", "calls", "-o",
                   str(out / "strace-count.txt"), *cmd]
        print(f"human-run: starting the engine ({args.mode}); play until the "
              "toon selection screen, wait 60 s there, then quit the game.",
              flush=True)
        threading.Thread(target=sample, args=(pid_holder, out / "samples.txt", stop),
                         daemon=True).start()
        with (out / "engine.log").open("wb") as log:
            proc = real_popen(cmd, cwd=str(kw.get("cwd", game)), env=env,
                              stdout=log, stderr=subprocess.STDOUT)
            pid_holder["engine"] = proc.pid
            rc = proc.wait()
        stop.set()
        print(f"human-run: engine exited with status {rc}", flush=True)
        return subprocess.CompletedProcess(cmd, rc)

    subprocess.Popen = start_engine  # type: ignore[assignment,misc]
    subprocess.run = start_engine    # type: ignore[assignment]

    cookie = ""
    try:
        launcher.Launcher().prepare_login()
    finally:
        cookie = os.environ.pop("TTR_PLAYCOOKIE", "")
        os.environ.pop("TTR_GAMESERVER", None)
        # The engine's own logs and settings, then scrub everything.
        for name in ("logs", "settings.json"):
            src = game / name
            if src.is_dir():
                shutil.copytree(src, out / "game-files" / name)
            elif src.is_file():
                (out / "game-files").mkdir(exist_ok=True)
                shutil.copy2(src, out / "game-files" / name)
        n = scrub(out, cookie)
        n += scrub(game, cookie)
        cookie = ""
        print(f"human-run: redacted the play cookie and login token {n} time(s) in the output; "
              f"files are in build/human-run/{args.mode}/", flush=True)
        shutil.rmtree(home, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
