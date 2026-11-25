#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Group an ELF file's undefined dynamic symbols by the library providing them.

Used by tools/ref/recon-static.sh in docker/ref-amd64 (Python 3.11 there, so
no 3.12-only syntax). Versioned imports are attributed by their version-need
entry; unversioned ones by searching the DT_NEEDED libraries (RUNPATH "."
means the ELF's own directory, then the system library path) for a defined
dynamic symbol of that name. Output: one "### library (count)" block per
library with the sorted symbol names, then "### unresolved".
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections import defaultdict

SYSTEM_DIRS = ["/lib/x86_64-linux-gnu", "/usr/lib/x86_64-linux-gnu", "/lib64"]


def readelf(*args: str) -> str:
    return subprocess.run(["readelf", *args], check=True, capture_output=True,
                          text=True).stdout


def needed_and_runpath(path: str) -> tuple[list[str], list[str]]:
    needed, runpath = [], []
    for line in readelf("-dW", path).splitlines():
        m = re.search(r"\((NEEDED|RUNPATH|RPATH)\).*\[(.*)\]", line)
        if not m:
            continue
        if m.group(1) == "NEEDED":
            needed.append(m.group(2))
        else:
            runpath.extend(m.group(2).split(":"))
    return needed, runpath


def version_files(path: str) -> dict[int, str]:
    """Map a version-need index (the "(N)" readelf prints after a versioned
    import) to the DT_NEEDED file that declares it. The index, not the
    version name, is what the dynamic linker binds by: GLIBC_2.2.5 appears
    under several glibc libraries."""
    result: dict[int, str] = {}
    current = None
    for line in readelf("-V", path).splitlines():
        m = re.search(r"File: (\S+)", line)
        if m:
            current = m.group(1)
            continue
        m = re.search(r"Name: \S+\s+Flags: \S+\s+Version: (\d+)", line)
        if m and current:
            result[int(m.group(1))] = current
    return result


def undefined_symbols(path: str) -> list[tuple[str, int | None, str]]:
    syms = []
    for line in readelf("--dyn-syms", "-W", path).splitlines():
        parts = line.split()
        if len(parts) < 8 or parts[6] != "UND":
            continue
        name = parts[7]
        bind = parts[4]
        index = None
        if "@" in name:
            name = name.split("@", 1)[0]
            if len(parts) > 8 and parts[8].startswith("("):
                index = int(parts[8].strip("()"))
        if not name:
            continue
        syms.append((name, index, bind))
    return syms


def defined_symbols(lib: str) -> set[str]:
    out = subprocess.run(["nm", "-D", "--defined-only", lib],
                         capture_output=True, text=True).stdout
    names = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            names.add(parts[2].split("@")[0])
    return names


def find_lib(name: str, search: list[str]) -> str | None:
    for d in search:
        candidate = os.path.join(d, name)
        if os.path.exists(candidate):
            return os.path.realpath(candidate)
    return None


def main() -> int:
    path = sys.argv[1]
    own_dir = os.path.dirname(os.path.abspath(path))
    needed, runpath = needed_and_runpath(path)
    search = [own_dir if r in (".", "$ORIGIN") else r for r in runpath]
    search += SYSTEM_DIRS
    vfiles = version_files(path)

    providers: dict[str, set[str]] = {}
    for lib in needed:
        located = find_lib(lib, search)
        providers[lib] = defined_symbols(located) if located else set()

    groups: dict[str, list[str]] = defaultdict(list)
    for name, version, bind in undefined_symbols(path):
        label = name + (" (weak)" if bind == "WEAK" else "")
        if version is not None and version in vfiles:
            groups[vfiles[version]].append(label)
            continue
        owner = next((lib for lib in needed if name in providers[lib]), None)
        groups[owner or "unresolved"].append(label)

    missing = [lib for lib in needed if not providers[lib]]
    total = sum(len(v) for v in groups.values())
    print(f"total undefined: {total}")
    if missing:
        print(f"needed libraries not found for resolution: {', '.join(missing)}")
    for lib in needed + ["unresolved"]:
        if lib in groups:
            print(f"### {lib} ({len(groups[lib])})")
            for sym in sorted(groups[lib]):
                print(f"    {sym}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
