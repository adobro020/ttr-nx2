# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for tools/guardrails/check.py, in throwaway git repositories."""
from __future__ import annotations

import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from tools.guardrails import check

# Built at run time so this file never contains a cookie assignment itself.
COOKIE_NAME = "TTR_" + "PLAYCOOKIE"
PIN = "af80b26bbf06cbd9d25c53b225003bd310c00252"
OTHER = "1111111111111111111111111111111111111111"


class Repo:
    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "test")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout

    def write(self, path: str, data: bytes | str) -> None:
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            data = data.encode()
        p.write_bytes(data)
        self.git("add", "-f", path)

    def gitlink(self, path: str, sha: str) -> None:
        self.git("update-index", "--add", "--cacheinfo",
                 f"160000,{sha},{path}")

    def commit(self, msg: str = "c") -> None:
        self.git("commit", "-q", "--no-verify", "-m", msg)


def run(*argv: str) -> tuple[int, str]:
    err = io.StringIO()
    with redirect_stderr(err), redirect_stdout(io.StringIO()):
        rc = check.main(list(argv))
    return rc, err.getvalue()


class GuardrailTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Repo(Path(self._tmp.name))
        self.repo.write("README.md", "hello\n")
        self.repo.write(check.LAUNCHER_PIN_FILE, PIN + "\n")
        self.repo.gitlink(check.LAUNCHER_PATH, PIN)
        self.repo.commit("base")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def staged(self) -> tuple[int, str]:
        return run("--staged", "--repo", str(self.repo.root))

    def test_clean_change_passes(self) -> None:
        self.repo.write("src/a.c", "int main(void) { return 0; }\n")
        self.assertEqual(self.staged()[0], 0)
        self.assertEqual(run("--all", "--repo", str(self.repo.root))[0], 0)

    def test_engine_binary_rejected(self) -> None:
        for name in ("TTREngine", "game/TTREngine64", "x/ttrengine.exe"):
            with self.subTest(name=name):
                self.repo.git("reset", "-q")
                self.repo.write(name, b"\x7fELF")
                rc, err = self.staged()
                self.assertEqual(rc, 1)
                self.assertIn("game-file", err)

    def test_multifile_rejected(self) -> None:
        self.repo.write("phase_3.mf", b"x")
        rc, err = self.staged()
        self.assertEqual(rc, 1)
        self.assertIn("game-file", err)

    def test_large_file_rejected(self) -> None:
        self.repo.write("big.bin", b"\0" * (check.MAX_BLOB_BYTES + 1))
        rc, err = self.staged()
        self.assertEqual(rc, 1)
        self.assertIn("large-file", err)

    def test_file_at_limit_passes(self) -> None:
        self.repo.write("ok.bin", b"\0" * check.MAX_BLOB_BYTES)
        self.assertEqual(self.staged()[0], 0)

    def test_cookie_assignments_rejected(self) -> None:
        lines = [
            f"{COOKIE_NAME}=abc123",
            f"export {COOKIE_NAME}='deadbeef'",
            f'env["{COOKIE_NAME}"] = "deadbeef"',
            f'{{"{COOKIE_NAME}": "deadbeef"}}',
        ]
        for line in lines:
            with self.subTest(line=line):
                self.repo.git("reset", "-q")
                self.repo.write("notes.txt", line + "\n")
                rc, err = self.staged()
                self.assertEqual(rc, 1)
                self.assertIn("play-cookie", err)
                self.assertNotIn("deadbeef", err)
                self.assertNotIn("abc123", err)

    def test_cookie_placeholders_pass(self) -> None:
        text = "\n".join([
            f"{COOKIE_NAME}=<value>",
            f"{COOKIE_NAME}=$cookie",
            f"{COOKIE_NAME}=[REDACTED]",
            f"{COOKIE_NAME}=***",
            f"os.environ['{COOKIE_NAME}'] = cookie",
            f"sets {COOKIE_NAME} in the environment",
        ]) + "\n"
        self.repo.write("adapter.py", text)
        rc, err = self.staged()
        self.assertEqual(rc, 0, err)

    def test_cookie_allowlist(self) -> None:
        self.repo.write(check.ALLOWLIST_FILE, "# reason\ndoc.md\n")
        self.repo.write("doc.md", f"{COOKIE_NAME}=abc123\n")
        self.assertEqual(self.staged()[0], 0)

    def test_launcher_pin_mismatch_rejected(self) -> None:
        self.repo.gitlink(check.LAUNCHER_PATH, OTHER)
        rc, err = self.staged()
        self.assertEqual(rc, 1)
        self.assertIn("launcher-pin", err)

    def test_launcher_missing_rejected_in_all_mode(self) -> None:
        self.repo.git("rm", "-q", "--cached", check.LAUNCHER_PATH)
        rc, err = run("--all", "--repo", str(self.repo.root))
        self.assertEqual(rc, 1)
        self.assertIn("not a submodule", err)

    def test_launcher_worktree_must_match_pin(self) -> None:
        sub = Repo(self.repo.root / check.LAUNCHER_PATH)
        sub.write("launcher.py", "print('upstream')\n")
        sub.commit("upstream")
        head = sub.git("rev-parse", "HEAD").strip()
        self.repo.write(check.LAUNCHER_PIN_FILE, head + "\n")
        self.repo.gitlink(check.LAUNCHER_PATH, head)
        self.assertEqual(self.staged()[0], 0)
        (sub.root / "launcher.py").write_text("print('patched')\n")
        rc, err = self.staged()
        self.assertEqual(rc, 1)
        self.assertIn("local changes", err)
        # Inside a hook git exports GIT_DIR and GIT_INDEX_FILE for the
        # superproject; the launcher check must still read the submodule.
        (sub.root / "launcher.py").write_text("print('upstream')\n")
        hook_env = {"GIT_DIR": str(self.repo.root / ".git"),
                    "GIT_INDEX_FILE": str(self.repo.root / ".git" / "index")}
        with mock.patch.dict(os.environ, hook_env):
            self.assertEqual(self.staged()[0], 0)
            (sub.root / "launcher.py").write_text("print('patched')\n")
            self.assertEqual(self.staged()[0], 1)
        # A commit that does not carry the submodule yet is not blocked.
        self.repo.git("update-index", "--force-remove", check.LAUNCHER_PATH)
        self.assertEqual(self.staged()[0], 0)

    def test_history_catches_file_removed_later(self) -> None:
        self.repo.write("TTREngine", b"\x7fELF")
        self.repo.commit("bad")
        self.repo.git("rm", "-q", "TTREngine")
        self.repo.commit("remove")
        rc, err = run("--history", "HEAD~2..HEAD", "--repo",
                      str(self.repo.root))
        self.assertEqual(rc, 1)
        self.assertIn("game-file", err)
        self.assertEqual(run("--all", "--repo", str(self.repo.root))[0], 0)


if __name__ == "__main__":
    unittest.main()
