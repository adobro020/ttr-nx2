#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Repository guard rails (CLAUDE.md rules 1, 3 and 4).

Fails when a change would put any of these into git:
  * a blob larger than 5 MB;
  * a path that looks like a TTR game file (TTREngine*, *.mf);
  * a Simple TTR Launcher submodule commit other than the pinned one, or a
    checked-out launcher tree that differs from that commit;
  * a line that assigns a value to TTR_PLAYCOOKIE.

Modes:
  --staged          what the next commit would add (pre-commit hook)
  --all             every tracked file in the index (CI, at HEAD)
  --history RANGE   every blob added by every commit in RANGE (CI, PRs)

Only the standard library is used so the hook runs on a bare Mac. Findings
name the rule and path; matched secret values are never printed (rule 4).
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

MAX_BLOB_BYTES = 5 * 1024 * 1024
GAME_FILE_PATTERNS = ("ttrengine*", "*.mf", "phase_*.mf")
LAUNCHER_PATH = "third_party/Simple-TTR-Launcher"
LAUNCHER_PIN_FILE = "third_party/launcher.pin"
ALLOWLIST_FILE = "tools/guardrails/cookie-allowlist.txt"
GITLINK_MODE = "160000"
ZERO_SHA = "0" * 40

# Two shapes (examples live in tests/unit/test_guardrails.py, built at run
# time, because writing them here would trip this very check):
#   1. env-style: the name, "=", then a value, optionally quoted;
#   2. the name used as a quoted key or subscript, then ":" or "=", then a
#      quoted literal value.
# Placeholders such as <value>, $VAR, {var}, [REDACTED] and *** and
# assignments from a variable deliberately do not match.
_VALUE = rb"[A-Za-z0-9+/=_.:-]{3,}"
COOKIE_RE = re.compile(
    rb"TTR_PLAYCOOKIE=[\"']?" + _VALUE
    + rb"|TTR_PLAYCOOKIE[\"']?\]?\s*[:=]\s*[\"']" + _VALUE + rb"[\"']"
)


@dataclass(frozen=True)
class Entry:
    path: str
    mode: str
    sha: str  # blob id, or commit id for a gitlink
    where: str  # "index" or a commit id, for messages


def git(repo: Path, *args: str, binary: bool = False,
        other_repo: bool = False) -> bytes | str:
    env = None
    if other_repo:
        # Inside a git hook, GIT_DIR, GIT_INDEX_FILE and friends point at the
        # superproject; a nested repository (the launcher submodule) must not
        # inherit them or git reads the wrong index.
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    out = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True,
        env=env,
    ).stdout
    return out if binary else out.decode()


def staged_entries(repo: Path) -> list[Entry]:
    raw = git(repo, "diff", "--cached", "--raw", "-z", "--no-abbrev", "--no-renames",
              "--diff-filter=ACMT")
    return list(_parse_raw(raw, "index"))


def all_entries(repo: Path) -> list[Entry]:
    out: list[Entry] = []
    for rec in git(repo, "ls-files", "-s", "-z").split("\0"):
        if not rec:
            continue
        meta, path = rec.split("\t", 1)
        mode, sha, _stage = meta.split()
        out.append(Entry(path, mode, sha, "index"))
    return out


def history_entries(repo: Path, rev_range: str) -> list[Entry]:
    out: list[Entry] = []
    for commit in git(repo, "rev-list", "--reverse", rev_range).split():
        raw = git(repo, "diff-tree", "-r", "--root", "--raw", "-z", "--no-abbrev",
                  "--no-renames", "--no-commit-id", "--diff-filter=ACMT",
                  commit)
        out.extend(_parse_raw(raw, commit[:12]))
    return out


def _parse_raw(raw: str, where: str):
    parts = raw.split("\0")
    i = 0
    while i + 1 < len(parts):
        meta, path = parts[i], parts[i + 1]
        i += 2
        if not meta.startswith(":"):
            continue
        _src_mode, dst_mode, _src_sha, dst_sha, _status = meta[1:].split()
        yield Entry(path, dst_mode, dst_sha, where)


def read_pin(repo: Path, where: str) -> str | None:
    try:
        if where == "index":
            data = git(repo, "show", f":{LAUNCHER_PIN_FILE}")
        else:
            data = git(repo, "show", f"{where}:{LAUNCHER_PIN_FILE}")
    except subprocess.CalledProcessError:
        return None
    assert isinstance(data, str)
    return data.strip() or None


def read_allowlist(repo: Path) -> set[str]:
    try:
        data = git(repo, "show", f":{ALLOWLIST_FILE}")
    except subprocess.CalledProcessError:
        return set()
    assert isinstance(data, str)
    return {ln.strip() for ln in data.splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")}


def check_entries(repo: Path, entries: list[Entry]) -> list[str]:
    problems: list[str] = []
    allow = read_allowlist(repo)
    for e in entries:
        name = e.path.rsplit("/", 1)[-1].lower()
        if any(fnmatch.fnmatchcase(name, p) for p in GAME_FILE_PATTERNS):
            problems.append(f"game-file: {e.path} ({e.where}) matches a TTR "
                            "game file pattern; game files never enter git")
        if e.mode == GITLINK_MODE:
            if e.path == LAUNCHER_PATH:
                pin = read_pin(repo, e.where)
                if pin != e.sha:
                    problems.append(
                        f"launcher-pin: {e.path} ({e.where}) points at "
                        f"{e.sha[:12]}, pinned is {(pin or 'missing')[:12]}; "
                        "the launcher source is never modified")
            continue
        if e.sha == ZERO_SHA:
            continue
        size = int(git(repo, "cat-file", "-s", e.sha))
        if size > MAX_BLOB_BYTES:
            problems.append(f"large-file: {e.path} ({e.where}) is {size} "
                            f"bytes; limit is {MAX_BLOB_BYTES}")
            continue
        if e.path in allow:
            continue
        blob = git(repo, "cat-file", "blob", e.sha, binary=True)
        assert isinstance(blob, bytes)
        for lineno, line in enumerate(blob.splitlines(), 1):
            if COOKIE_RE.search(line):
                # Never echo the line: it may hold a live cookie (rule 4).
                problems.append(f"play-cookie: {e.path}:{lineno} ({e.where}) "
                                "assigns a value to TTR_PLAYCOOKIE")
    return problems


def check_launcher_worktree(repo: Path) -> list[str]:
    """The checked-out launcher must be exactly the pinned commit, clean."""
    sub = repo / LAUNCHER_PATH
    if not (sub / ".git").exists():
        return []  # not checked out here; the gitlink check still applies
    if not str(git(repo, "ls-files", "-s", "--", LAUNCHER_PATH)).strip():
        return []  # not a submodule in this index (e.g. the first commit)
    pin = read_pin(repo, "index")
    problems: list[str] = []
    head = str(git(sub, "rev-parse", "HEAD", other_repo=True)).strip()
    if head != pin:
        problems.append(f"launcher-pin: checked-out launcher is at "
                        f"{head[:12]}, pinned is {(pin or 'missing')[:12]}")
    dirty = str(git(sub, "status", "--porcelain", "--ignored=no",
                    other_repo=True))
    if dirty.strip():
        problems.append("launcher-pin: the launcher working tree has local "
                        "changes; it must be byte-identical to upstream")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--all", action="store_true")
    mode.add_argument("--history", metavar="RANGE")
    ap.add_argument("--repo", default=".", type=Path)
    args = ap.parse_args(argv)
    repo: Path = args.repo.resolve()

    if args.staged:
        entries = staged_entries(repo)
    elif args.all:
        entries = all_entries(repo)
    else:
        entries = history_entries(repo, args.history)

    problems = check_entries(repo, entries)
    if args.staged or args.all:
        problems += check_launcher_worktree(repo)
        if args.all and LAUNCHER_PATH not in {e.path for e in entries}:
            problems.append(f"launcher-pin: {LAUNCHER_PATH} is not a "
                            "submodule in this tree")

    for p in problems:
        print(f"guardrails: FAIL {p}", file=sys.stderr)
    if problems:
        print(f"guardrails: {len(problems)} problem(s); see CLAUDE.md "
              "rules 1, 3 and 4", file=sys.stderr)
        return 1
    print(f"guardrails: ok ({len(entries)} entries checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
