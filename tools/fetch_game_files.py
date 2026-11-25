#!/usr/bin/env python3.12
# SPDX-License-Identifier: GPL-2.0-only
"""Download the Linux TTR game files with the launcher's own patcher.

Run inside docker/bench-arm64 (Linux, so ``sys.platform == 'linux'`` makes
the upstream patcher select the Linux files):

    make fetch-game        # = python3.12 tools/fetch_game_files.py --dest ref/game

This calls the **unmodified** ``patcher.Patcher().check_update()`` from the
pinned launcher submodule. It needs no login: the mirrors list and the patch
manifest are public. Files land in ``ref/game/`` (git-ignored; CLAUDE.md
rule 1). Run it rarely: every run asks TTR's servers for the manifest and
downloads whatever is missing or stale (CLAUDE.md rule 5).

After the patcher returns, a summary (file names, sizes, SHA-1) is written to
``ref/game-files.json`` so the recon documents can cite exact versions
without copying any game data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAUNCHER_DIR = ROOT / "third_party" / "Simple-TTR-Launcher"

# The manifest path TTR's login API returns in its success response
# (ToontownRewritten/api-doc login.md, "Non-queued response").
DEFAULT_MANIFEST = "/content/patchmanifest.txt"


def sha1_of(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dest", default=str(ROOT / "ref" / "game"))
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--summary", default=str(ROOT / "ref" / "game-files.json"))
    args = parser.parse_args()

    if not sys.platform.startswith("linux"):
        print("fetch_game_files: run this in a Linux container "
              "(make fetch-game); the patcher picks files by sys.platform",
              file=sys.stderr)
        return 2

    dest = Path(args.dest).resolve()
    if ROOT not in dest.parents or dest.relative_to(ROOT).parts[0] != "ref":
        print(f"fetch_game_files: refusing to write outside ref/: {dest}",
              file=sys.stderr)
        return 2
    # The patcher asks on the terminal before creating a missing directory
    # (patcher.py __check_install_path); create it so the run is unattended.
    dest.mkdir(parents=True, exist_ok=True)

    # Import the launcher modules exactly as shipped. Do not write .pyc files
    # into the submodule (its tree must stay byte-identical, rule 3).
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(LAUNCHER_DIR))
    import patcher  # noqa: E402  (upstream module, unmodified)

    print(f"fetch_game_files: Patcher().check_update({str(dest)!r}, "
          f"{args.manifest!r})", flush=True)
    started = time.monotonic()
    ok = patcher.Patcher().check_update(str(dest), args.manifest)
    elapsed = time.monotonic() - started
    print(f"fetch_game_files: check_update returned {ok} after {elapsed:.0f} s",
          flush=True)
    if not ok:
        return 1

    files = []
    for path in sorted(p for p in dest.rglob("*") if p.is_file()):
        files.append({
            "name": str(path.relative_to(dest)),
            "size": path.stat().st_size,
            "sha1": sha1_of(path),
            "executable": os.access(path, os.X_OK),
        })
    summary = {
        "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "manifest": args.manifest,
        "platform": sys.platform,
        "files": files,
        "total_bytes": sum(f["size"] for f in files),
    }
    Path(args.summary).write_text(json.dumps(summary, indent=2) + "\n",
                                  encoding="utf-8")
    print(f"fetch_game_files: {len(files)} files, "
          f"{summary['total_bytes'] / 1e9:.2f} GB; summary in {args.summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
