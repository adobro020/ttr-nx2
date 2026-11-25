# SPDX-License-Identifier: GPL-2.0-only
"""Patcher contract: full downloads, bsdiff updates, hash checks, mirror
failover and retries, driven through the unmodified ``patcher.Patcher``."""

from __future__ import annotations

import hashlib
import sys

import pytest

from tools.fake_ttr_api import MANIFEST_PATH, MIRROR_HOSTS, Faults, GameFixture
from tools.fake_ttr_api.fixtures import ENGINE


def sha1_file(path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def install_old(env, fixture: GameFixture) -> None:
    """A previous install: old versions where a patch exists, current
    versions otherwise."""
    env.game.mkdir(exist_ok=True)
    for f in fixture.files:
        if "linux" in f.only:
            (env.game / f.name).write_bytes(f.old if f.old is not None else f.new)


def check_update(env) -> bool:
    return env.up.patcher.Patcher().check_update(str(env.game), MANIFEST_PATH)


def test_incremental_bsdiff_update(env, fake_api, capsys):
    fake = fake_api()
    install_old(env, fake.fixture)
    assert check_update(env) is True
    fx = fake.fixture
    patched = [f.name for f in fx.files if f.old is not None]
    assert sorted(fake.downloaded()) == sorted(fx.patch_download_name(n) for n in patched)
    for f in fx.files:
        if "linux" in f.only:
            assert sha1_file(env.game / f.name) == fx.manifest[f.name]["hash"]


def test_up_to_date_downloads_nothing(env, fake_api):
    fake = fake_api()
    env.game.mkdir()
    for f in fake.fixture.files:
        (env.game / f.name).write_bytes(f.new)
    assert check_update(env) is True
    assert fake.downloaded() == []


def test_unknown_local_version_downloads_in_full(env, fake_api):
    fake = fake_api()
    env.game.mkdir()
    (env.game / "resources_a.bin").write_bytes(b"neither old nor new")
    assert check_update(env) is True
    assert fake.fixture.full_download_name("resources_a.bin") in fake.downloaded()


def test_linux_selects_linux_files(env, fake_api, monkeypatch):
    """Patcher.__get_system uses sys.platform: on the bench and the console it
    is 'linux', which must pick exactly the files whose "only" has 'linux'."""
    monkeypatch.setattr(sys, "platform", "linux")
    fake = fake_api()
    env.game.mkdir()
    assert check_update(env) is True
    names = {n.split(".")[0] for n in fake.downloaded()}
    assert "windows_only" not in names and ENGINE in names


@pytest.mark.parametrize("target", ["full", "patch"])
def test_compressed_hash_mismatch_fails_after_retries(env, fake_api, capsys, target):
    fixture = GameFixture.build()
    if target == "full":
        bad = fixture.full_download_name("resources_a.bin")
    else:
        bad = fixture.patch_download_name("resources_b.bin")
    fake = fake_api(fixture=fixture, faults=Faults(corrupt_downloads={bad}))
    if target == "patch":
        install_old(env, fixture)
    else:
        env.game.mkdir()
    assert check_update(env) is False
    assert fake.downloaded().count(bad) == 3       # retry_count = 3
    assert "One or more downloads failed." in capsys.readouterr().out


def test_decompressed_hash_mismatch(env, fake_api, capsys):
    fixture = GameFixture.build()
    fixture.manifest["resources_a.bin"]["hash"] = "0" * 40
    fake_api(fixture=fixture)
    env.game.mkdir()
    assert check_update(env) is False
    out = capsys.readouterr().out
    assert "Failed to decompress resources_a.bin." in out


def test_post_patch_hash_mismatch(env, fake_api, capsys):
    fixture = GameFixture.build()
    install_old(env, fixture)
    fixture.manifest["resources_b.bin"]["hash"] = "0" * 40
    fake_api(fixture=fixture)
    assert check_update(env) is False
    assert "Failed to apply patch to resources_b.bin" in capsys.readouterr().out


def test_one_mirror_down_fails_over(env, fake_api, monkeypatch):
    """A failing mirror is dropped from the shared list and the retry uses the
    next one (__download_file removes mirrors[0] on RequestException).

    One worker thread: with several, two threads can both pass the
    ``len(mirrors) > 1`` check and both ``remove()`` the same mirror, and the
    second ValueError escapes the thread pool (an upstream race recorded in
    docs/recon/launcher-contract.md; the adapter must not rely on failover
    under concurrency)."""
    import os
    monkeypatch.setattr(os, "cpu_count", lambda: 1)
    fake = fake_api(faults=Faults(down_hosts={MIRROR_HOSTS[0]}))
    env.game.mkdir()
    assert check_update(env) is True
    for f in fake.fixture.files:
        if "linux" in f.only:
            assert sha1_file(env.game / f.name) == fake.fixture.manifest[f.name]["hash"]


def test_all_mirrors_down(env, fake_api, capsys):
    fake_api(faults=Faults(down_hosts=set(MIRROR_HOSTS)))
    env.game.mkdir()
    assert check_update(env) is False
    assert "One or more downloads failed." in capsys.readouterr().out


def test_mirror_list_unavailable(env, fake_api, capsys):
    fake = fake_api(faults=Faults(mirrors_http_errors=99))
    env.game.mkdir()
    assert check_update(env) is False
    assert len([r for r in fake.requests if r.path == "/api/mirrors"]) == 3
    assert "Could not get the download mirrors." in capsys.readouterr().out


def test_manifest_retry_then_success(env, fake_api):
    fake_api(faults=Faults(manifest_http_errors=2))
    env.game.mkdir()
    assert check_update(env) is True
    assert env.sleeps.count(10) >= 2               # retry_timeout = 10


def test_manifest_not_json(env, fake_api, capsys):
    """requests' JSONDecodeError subclasses RequestException, so a non-JSON
    manifest is retried 3 times and reported as a download failure; the
    patcher's "Could not decode" branch is unreachable with requests >= 2.27
    (recorded in docs/recon/launcher-contract.md)."""
    fake_api(faults=Faults(manifest_not_json=True))
    env.game.mkdir()
    assert check_update(env) is False
    out = capsys.readouterr().out
    assert out.count("Retrying...") == 3
    assert "Could not download the patch manifest." in out
    assert "Could not decode" not in out


def test_declining_to_create_install_dir(env, fake_api):
    fake = fake_api()
    env.term.expect("Enter 1 to confirm or 0 to cancel: ", "0")
    assert check_update(env) is False
    assert not env.game.exists() and fake.downloaded() == []
