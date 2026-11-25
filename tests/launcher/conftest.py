# SPDX-License-Identifier: GPL-2.0-only
"""Fixtures that run the unmodified Simple TTR Launcher against the fake API.

Nothing in third_party/Simple-TTR-Launcher is changed or copied. Its modules
are imported from the submodule and adapted from outside, the way Phase 5's
adapter will: terminal input is scripted, ``helper.get_launcher_path`` points
at a temporary directory (so launcher.json is never written into the
submodule), sockets are redirected to the fake server, and the process
launch is recorded instead of run.
"""

from __future__ import annotations

import builtins
import json
import platform
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import keyring
import keyring.backend
import pytest

from tools.fake_ttr_api import HOSTS, FakeTTR, Faults, redirect_hosts

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER_DIR = ROOT / "third_party" / "Simple-TTR-Launcher"


# -- the upstream modules ------------------------------------------------------
@dataclass
class Upstream:
    helper: Any
    encrypt: Any
    patcher: Any
    launcher: Any
    pwinput: Any


@pytest.fixture(scope="session")
def upstream() -> Upstream:
    # No .pyc files in the submodule (rule 3: byte-identical tree).
    sys.dont_write_bytecode = True
    if str(LAUNCHER_DIR) not in sys.path:
        sys.path.insert(0, str(LAUNCHER_DIR))
    import encrypt
    import helper
    import launcher
    import patcher
    import pwinput
    for mod in (helper, encrypt, patcher, launcher):
        assert Path(mod.__file__).parent == LAUNCHER_DIR, mod.__file__
    return Upstream(helper, encrypt, patcher, launcher, pwinput)


# -- terminal ------------------------------------------------------------------
class Terminal:
    """Scripted answers for ``input()`` and ``pwinput.pwinput()``.

    ``expect(prompt, answer)`` queues one answer; the prompt shown must equal
    ``prompt``. Running out of answers fails the test instead of hanging."""

    def __init__(self) -> None:
        self.script: list[tuple[str, str, str]] = []  # (kind, prompt, answer)
        self.seen: list[tuple[str, str]] = []

    def expect(self, prompt: str, answer: str, kind: str = "input") -> "Terminal":
        self.script.append((kind, prompt, answer))
        return self

    def secret(self, prompt: str, answer: str) -> "Terminal":
        return self.expect(prompt, answer, kind="pwinput")

    def _answer(self, kind: str, prompt: str) -> str:
        self.seen.append((kind, prompt))
        if not self.script:
            raise AssertionError(f"unscripted {kind} prompt: {prompt!r}")
        want_kind, want_prompt, answer = self.script.pop(0)
        assert (kind, prompt) == (want_kind, want_prompt), \
            f"expected {want_kind} {want_prompt!r}, got {kind} {prompt!r}"
        return answer

    def input(self, prompt: str = "") -> str:
        return self._answer("input", prompt)

    def pwinput(self, prompt: str = "Password: ", mask: str = "*") -> str:
        return self._answer("pwinput", prompt)

    def done(self) -> None:
        assert not self.script, f"answers never asked for: {self.script}"


class MemoryKeyring(keyring.backend.KeyringBackend):
    """Keeps tests away from the real OS keychain."""
    priority = 1  # type: ignore[assignment]

    def __init__(self) -> None:
        super().__init__()
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self.store.pop((service, username), None)


@dataclass
class Launch:
    func: str
    kwargs: dict[str, Any]
    env: dict[str, str]


@dataclass
class Env:
    """Everything a test needs around one launcher run."""
    up: Upstream
    term: Terminal
    home: Path            # stands in for the launcher's own directory
    game: Path            # TTR install directory
    keyring: MemoryKeyring
    sleeps: list[float] = field(default_factory=list)
    launches: list[Launch] = field(default_factory=list)

    def write_settings(self, **launcher: Any) -> None:
        settings = {
            "accounts": {},
            "launcher": {
                "ttr-dir": str(self.game),
                "use-stored-accounts": False,
                "use-password-encryption": False,
                "display-logging": False,
                "use-os-keyring": False,
            },
        }
        settings["launcher"].update(launcher)
        (self.home / "launcher.json").write_text(json.dumps(settings))

    def settings(self) -> dict[str, Any]:
        return json.loads((self.home / "launcher.json").read_text())


@pytest.fixture
def env(upstream: Upstream, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> Iterator[Env]:
    home = tmp_path / "launcher"
    home.mkdir()
    term = Terminal()
    ring = MemoryKeyring()
    e = Env(up=upstream, term=term, home=home, game=tmp_path / "game", keyring=ring)

    monkeypatch.chdir(home)                  # helper looks for ./login.json
    monkeypatch.setattr(sys, "argv", ["main.py"])  # launcher reads len(sys.argv)
    monkeypatch.setattr(upstream.helper, "get_launcher_path", lambda: str(home))
    monkeypatch.setattr(builtins, "input", term.input)
    monkeypatch.setattr(upstream.pwinput, "pwinput", term.pwinput)
    monkeypatch.setattr(time, "sleep", e.sleeps.append)
    # The bench and console run Linux; launcher.py picks the binary by
    # platform.system() (__start_game).
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    keyring.set_keyring(ring)
    for name in ("TTR_GAMESERVER", "TTR_PLAYCOOKIE"):
        monkeypatch.delenv(name, raising=False)

    import os

    def record(func: str):  # type: ignore[no-untyped-def]
        def fake(*args: Any, **kwargs: Any) -> Any:
            assert not args, "launcher passes everything as keywords"
            e.launches.append(Launch(func, kwargs, dict(os.environ)))
            return subprocess.CompletedProcess(kwargs.get("args"), 0)
        return fake

    monkeypatch.setattr(subprocess, "Popen", record("Popen"))
    monkeypatch.setattr(subprocess, "run", record("run"))
    yield e
    term.done()


@pytest.fixture
def fake_api(tmp_path: Path) -> Iterator[Any]:
    """``fake_api(scenario, faults=..., closed=...)`` starts a FakeTTR and
    redirects the launcher's connections to it for the rest of the test."""
    import contextlib
    stack = contextlib.ExitStack()

    def start(scenario: str = "success", faults: Faults | None = None,
              closed: set[str] = frozenset(), fixture: Any = None) -> FakeTTR:
        fake = stack.enter_context(
            FakeTTR(tmp_path / "fake", scenario, fixture=fixture, faults=faults))
        stack.enter_context(redirect_hosts({h: fake.port for h in HOSTS},
                                           str(fake.certs.ca_pem), closed))
        return fake

    with stack:
        yield start
