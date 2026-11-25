# SPDX-License-Identifier: GPL-2.0-only
"""Small synthetic "game" files, their bz2 downloads, bsdiff patches and the
patch manifest that describes them, in the format the pinned launcher's
patcher reads (third_party/Simple-TTR-Launcher/patcher.py, __check_patch):

    {"<file>": {"dl": "<remote .bz2 name>", "hash": "<sha1 of file>",
                "compHash": "<sha1 of .bz2>", "only": ["linux", ...],
                "patches": {"<sha1 of old file>": {
                    "filename": "<remote patch .bz2 name>",
                    "patchHash": "<sha1 of patch>",
                    "compPatchHash": "<sha1 of patch .bz2>"}}}}

Nothing here is TTR data. Contents are pseudo-random bytes from a fixed
seed, so every run produces the same files and hashes.
"""

from __future__ import annotations

import bz2
import hashlib
import random
from dataclasses import dataclass, field

import bsdiff4


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def _blob(seed: str, size: int) -> bytes:
    return random.Random(seed).randbytes(size)


def _edit(data: bytes, seed: str) -> bytes:
    """A plausible new version: some bytes changed, a block inserted."""
    rng = random.Random(seed)
    out = bytearray(data)
    for _ in range(32):
        out[rng.randrange(len(out))] = rng.randrange(256)
    at = rng.randrange(len(out))
    return bytes(out[:at] + rng.randbytes(1024) + out[at:])


# The engine file is a tiny script so a launch test can check its mode bits;
# the name matches what launcher.py starts on Linux (linux_bin).
ENGINE = "TTREngine"
NATIVE = ("linux", "darwin")  # sys.platform values the tests run on


@dataclass
class GameFile:
    name: str
    old: bytes | None  # previous version a patch exists from (None: no patch)
    new: bytes
    only: tuple[str, ...] = NATIVE


@dataclass
class GameFixture:
    files: list[GameFile]
    # remote name -> served bytes (bz2 of a full file or of a patch)
    downloads: dict[str, bytes] = field(default_factory=dict)
    manifest: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def build(cls) -> "GameFixture":
        a_old = _blob("fixture-a", 96 * 1024)
        b_old = _blob("fixture-b", 48 * 1024)
        files = [
            GameFile(ENGINE, None, b"#!/bin/sh\necho fake engine\n"),
            GameFile("resources_a.bin", a_old, _edit(a_old, "a-v2")),
            GameFile("resources_b.bin", b_old, _edit(b_old, "b-v2")),
            # Only for Windows: must never be downloaded on Linux or macOS.
            GameFile("windows_only.dll", None, _blob("win", 4096),
                     only=("win32", "win64")),
        ]
        fixture = cls(files)
        for f in files:
            comp = bz2.compress(f.new)
            dl = f"{f.name}.{sha1(f.new)[:10]}.bz2"
            fixture.downloads[dl] = comp
            entry = {"dl": dl, "hash": sha1(f.new), "compHash": sha1(comp),
                     "only": list(f.only), "patches": {}}
            if f.old is not None:
                patch = bsdiff4.diff(f.old, f.new)
                pcomp = bz2.compress(patch)
                pname = f"{f.name}.{sha1(f.old)[:8]}-{sha1(f.new)[:8]}.patch.bz2"
                fixture.downloads[pname] = pcomp
                entry["patches"][sha1(f.old)] = {
                    "filename": pname, "patchHash": sha1(patch),
                    "compPatchHash": sha1(pcomp)}
            fixture.manifest[f.name] = entry
        return fixture

    def file(self, name: str) -> GameFile:
        return next(f for f in self.files if f.name == name)

    def full_download_name(self, name: str) -> str:
        return self.manifest[name]["dl"]

    def patch_download_name(self, name: str) -> str:
        (entry,) = self.manifest[name]["patches"].values()
        return entry["filename"]
