# SPDX-License-Identifier: GPL-2.0-only
"""Login contract: every login outcome of the pinned launcher, end to end
against the fake API, through to the recorded game launch."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess

import pytest

from tools.fake_ttr_api import CDN_HOST, LOGIN_HOST, MANIFEST_PATH, Faults
from tools.fake_ttr_api.fixtures import ENGINE
from tools.fake_ttr_api.server import GAMESERVER

USER, PASSWORD = "fake-toon", "fake-password-1"


def sha1_file(path: os.PathLike[str]) -> str:
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()


def login_forms(fake):
    return [r.form for r in fake.requests_to(LOGIN_HOST, "/api/login")]


def prompt_credentials(env):
    env.term.expect("Enter username: ", USER).secret("Enter password: ", PASSWORD)


def run_login(env):
    env.up.launcher.Launcher().prepare_login()


def assert_no_secrets(capsys, fake):
    out = capsys.readouterr()
    for secret in (fake.cookie, PASSWORD, *fake.tokens.values()):
        assert secret not in out.out and secret not in out.err
    return out.out


def test_success_fresh_install_and_launch(env, fake_api, capsys):
    """Fresh install: the install directory does not exist, the patcher asks
    to create it, downloads every file for this platform in full, then the
    launcher starts TTREngine with the gameserver and cookie in os.environ."""
    fake = fake_api("success")
    env.write_settings()
    prompt_credentials(env)
    env.term.expect("Enter 1 to confirm or 0 to cancel: ", "1")

    run_login(env)

    assert fake.errors == []
    assert login_forms(fake) == [{"username": USER, "password": PASSWORD}]
    assert len(fake.requests_to(LOGIN_HOST, "/api/mirrors")) == 1
    assert len(fake.requests_to(CDN_HOST, MANIFEST_PATH)) == 1
    fx = fake.fixture
    wanted = {f.name for f in fx.files if "linux" in f.only}
    assert sorted(fake.downloaded()) == sorted(fx.full_download_name(n) for n in wanted)
    for name in wanted:
        assert sha1_file(env.game / name) == fx.manifest[name]["hash"]
    assert not (env.game / "windows_only.dll").exists()
    assert sorted(os.listdir(env.game)) == sorted(wanted)  # temp dir cleaned

    engine = env.game / ENGINE
    assert stat.S_IMODE(engine.stat().st_mode) & 0o111 == 0o111
    (launch,) = env.launches
    assert launch.func == "Popen"
    assert launch.kwargs == {
        "args": str(engine), "cwd": str(env.game),
        "stdout": subprocess.DEVNULL, "stderr": subprocess.STDOUT,
        "start_new_session": True}
    assert launch.env["TTR_GAMESERVER"] == GAMESERVER
    assert launch.env["TTR_PLAYCOOKIE"] == fake.cookie
    out = assert_no_secrets(capsys, fake)
    assert "Requesting login..." in out and "Login successful!" in out


def test_display_logging_uses_subprocess_run(env, fake_api, capsys):
    fake = fake_api("success")
    env.write_settings(**{"display-logging": True})
    env.game.mkdir()
    prompt_credentials(env)
    run_login(env)
    (launch,) = env.launches
    assert launch.func == "run"
    assert launch.kwargs == {"args": str(env.game / ENGINE),
                             "cwd": str(env.game), "check": False}
    assert launch.env["TTR_PLAYCOOKIE"] == fake.cookie
    assert_no_secrets(capsys, fake)


@pytest.mark.parametrize("scenario,message", [
    ("failure", "Fake: incorrect username or password."),
    ("failure_no_banner", "Username or password may be incorrect"),
])
def test_failure(env, fake_api, capsys, scenario, message):
    fake = fake_api(scenario)
    env.write_settings()
    prompt_credentials(env)
    run_login(env)
    assert fake.errors == [] and fake.login_done()
    assert fake.requests_to(CDN_HOST) == [] and env.launches == []
    out = assert_no_secrets(capsys, fake)
    assert message in out and "Login failed!" in out


def test_partial_then_second_partial_then_success(env, fake_api, capsys):
    """Two-factor then ToonGuard: each banner is shown, each token prompt
    answered; trailing whitespace is stripped; authToken echoes the last
    responseToken (the fake checks this)."""
    fake = fake_api("partial")
    env.write_settings()
    env.game.mkdir()
    prompt_credentials(env)
    env.term.expect("Enter token: ", "123456 \n").expect("Enter token: ", "ABCDEF")
    run_login(env)
    assert fake.errors == [] and fake.login_done()
    forms = login_forms(fake)
    assert [f.get("appToken") for f in forms] == [None, "123456", "ABCDEF"]
    assert len(env.launches) == 1
    out = assert_no_secrets(capsys, fake)
    assert "Fake: please enter an authenticator token." in out
    assert "Fake: please enter a ToonGuard code." in out


def test_partial_rejected(env, fake_api, capsys):
    fake = fake_api("partial_rejected")
    env.write_settings()
    prompt_credentials(env)
    env.term.expect("Enter token: ", "000000")
    run_login(env)
    assert fake.errors == [] and env.launches == []
    out = assert_no_secrets(capsys, fake)
    assert "Fake: too many token attempts." in out and "Login failed!" in out


def test_queue_positions_decrease_then_success(env, fake_api, capsys):
    """Queue: position printed each round, waits eta seconds (minimum 1),
    resends only the queueToken."""
    fake = fake_api("queue")
    env.write_settings()
    env.game.mkdir()
    prompt_credentials(env)
    run_login(env)
    assert fake.errors == [] and fake.login_done()
    assert env.sleeps == [1, 2, 1]
    out = assert_no_secrets(capsys, fake)
    positions = [line for line in out.splitlines() if "queued in position" in line]
    assert positions == [f"You are queued in position {n}." for n in (3, 2, 1)]
    assert len(env.launches) == 1


def test_queue_failure(env, fake_api, capsys):
    fake = fake_api("queue_failure")
    env.write_settings()
    prompt_credentials(env)
    run_login(env)
    assert fake.errors == [] and env.launches == []
    assert "Fake: the queue closed." in assert_no_secrets(capsys, fake)


def test_login_server_errors_retry_then_succeed(env, fake_api, capsys):
    """helper.retry(3, 5, ...): two HTTP 500s, then success."""
    fake = fake_api("success", faults=Faults(login_http_errors=2))
    env.write_settings()
    env.game.mkdir()
    prompt_credentials(env)
    run_login(env)
    assert len(login_forms(fake)) == 3
    assert env.sleeps[:2] == [5, 5]
    assert len(env.launches) == 1
    assert assert_no_secrets(capsys, fake).count("Retrying...") == 2


@pytest.mark.parametrize("how", ["http-500", "refused"])
def test_login_network_failure_after_retries(env, fake_api, capsys, how):
    if how == "http-500":
        fake = fake_api("success", faults=Faults(login_http_errors=99))
    else:
        fake = fake_api("success", closed={LOGIN_HOST})
    env.write_settings()
    prompt_credentials(env)
    run_login(env)
    assert env.sleeps == [5, 5, 5]
    assert env.launches == []
    out = assert_no_secrets(capsys, fake)
    assert "Could not connect to the Toontown Rewritten login server." in out
    assert "Login failed!" in out


def test_missing_engine_after_update(env, fake_api, capsys):
    """If TTREngine is absent after patching, the launcher reports it."""
    from tools.fake_ttr_api import GameFixture
    fixture = GameFixture.build()
    del fixture.manifest[ENGINE]
    fake = fake_api("success", fixture=fixture)
    env.write_settings()
    env.game.mkdir()
    prompt_credentials(env)
    run_login(env)
    assert env.launches == []
    assert "Could not find Toontown Rewritten." in assert_no_secrets(capsys, fake)
