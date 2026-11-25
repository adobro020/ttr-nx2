# SPDX-License-Identifier: GPL-2.0-only
"""Stored accounts: keyring off with master-password encryption (Argon2id
key derivation, Fernet encryption), the keyring path, and a direct Encrypt
round trip. Phase 5 stores accounts this way on the SD card (ADR seed 8)."""

from __future__ import annotations

import json

from tools.fake_ttr_api import LOGIN_HOST

USER, PASSWORD, MASTER = "fake-toon", "fake-password-1", "fake-master-pw"


def add_account_with_new_master(env):
    """Launcher.add_account() on a fresh, keyring-off install: storing the
    first account turns on account storage, which (keyring off, encryption
    off) asks for a new master password and encrypts the account."""
    env.write_settings()
    env.term.expect("Enter username to store or 0 to cancel: ", USER)
    env.term.secret("Enter password to store: ", PASSWORD)
    env.term.secret("Create a master password: ", MASTER)
    assert env.up.launcher.Launcher().add_account() is True


def test_store_encrypted_account_then_login(env, fake_api, capsys):
    fake = fake_api("success")
    add_account_with_new_master(env)

    raw = (env.home / "launcher.json").read_text()
    assert PASSWORD not in raw and MASTER not in raw
    s = json.loads(raw)
    cfg = s["launcher"]
    assert cfg["use-stored-accounts"] is True
    assert cfg["use-password-encryption"] is True
    assert cfg["use-os-keyring"] is False
    assert cfg["hashing-params"] == {"t": 3, "m": 65536, "p": 4}
    assert {"salt-verification", "password-verification"} <= set(cfg)
    acc = s["accounts"]["account1"]
    assert acc["username"] == USER and set(acc) == {"username", "password", "salt"}
    assert acc["password"].startswith("gAAAA")  # Fernet token

    # A new process: one stored account, so no selection prompt; only the
    # master password is asked, then the decrypted password is sent.
    env.game.mkdir()
    env.term.secret("Enter your master password: ", MASTER)
    env.up.launcher.Launcher().prepare_login()
    forms = [r.form for r in fake.requests_to(LOGIN_HOST, "/api/login")]
    assert forms == [{"username": USER, "password": PASSWORD}]
    assert len(env.launches) == 1
    out = capsys.readouterr().out
    assert PASSWORD not in out and MASTER not in out


def test_wrong_master_password_three_times(env, fake_api, capsys):
    fake = fake_api("success")
    add_account_with_new_master(env)
    for _ in range(3):
        env.term.secret("Enter your master password: ", "wrong")
    env.up.launcher.Launcher().prepare_login()
    assert fake.requests_to(LOGIN_HOST, "/api/login") == []
    out = capsys.readouterr().out
    assert out.count("The password entered was incorrect.") == 3
    assert "You have made too many password attempts." in out


def test_select_among_several_accounts(env, fake_api):
    fake = fake_api("success")
    add_account_with_new_master(env)
    env.term.expect("Enter username to store or 0 to cancel: ", "second-toon")
    env.term.secret("Enter password to store: ", "second-password")
    env.term.secret("Enter your master password: ", MASTER)
    assert env.up.launcher.Launcher().add_account() is True
    env.game.mkdir()
    env.term.expect("Enter account number or 0 to cancel: ", "7")  # out of range
    env.term.expect("Enter account number or 0 to cancel: ", "x")  # not a number
    env.term.expect("Enter account number or 0 to cancel: ", "2")
    env.term.secret("Enter your master password: ", MASTER)
    env.up.launcher.Launcher().prepare_login()
    forms = [r.form for r in fake.requests_to(LOGIN_HOST, "/api/login")]
    assert forms == [{"username": "second-toon", "password": "second-password"}]


def test_disable_encryption_decrypts(env):
    add_account_with_new_master(env)
    env.term.expect("Enter 1 to confirm or 0 to cancel: ", "1")
    env.term.secret("Enter your master password: ", MASTER)
    env.up.launcher.Launcher().manage_password_encryption()
    s = env.settings()
    assert s["launcher"]["use-password-encryption"] is False
    assert s["accounts"]["account1"] == {"username": USER, "password": PASSWORD}


def test_os_keyring_path(env, fake_api):
    """Keyring on (upstream default): the password goes to the keyring and
    launcher.json holds the KEYRING_PASS placeholder. On the console there is
    no OS keyring; Phase 5 turns this off (ADR seed 8)."""
    fake = fake_api("success")
    env.write_settings(**{"use-os-keyring": True})
    env.term.expect("Enter username to store or 0 to cancel: ", USER)
    env.term.secret("Enter password to store: ", PASSWORD)
    assert env.up.launcher.Launcher().add_account() is True
    s = env.settings()
    assert s["accounts"]["account1"] == {"username": USER, "password": "KEYRING_PASS"}
    assert s["launcher"]["use-password-encryption"] is False
    assert env.keyring.store == {("Simple-TTR-Launcher", USER): PASSWORD}
    env.game.mkdir()
    env.up.launcher.Launcher().prepare_login()
    forms = [r.form for r in fake.requests_to(LOGIN_HOST, "/api/login")]
    assert forms == [{"username": USER, "password": PASSWORD}]


def test_encrypt_round_trip(env):
    enc = env.up.encrypt.Encrypt({"launcher": {"use-password-encryption": False}})
    token, salt = enc.encrypt(MASTER.encode(), PASSWORD)
    assert token != PASSWORD
    assert enc.decrypt(MASTER.encode(), token, salt) == PASSWORD
    import cryptography.fernet
    try:
        enc.decrypt(b"wrong", token, salt)
    except cryptography.fernet.InvalidToken:
        pass
    else:
        raise AssertionError("wrong master password decrypted the token")


def test_default_settings_file(env):
    """First run without launcher.json: the defaults written by
    helper.load_launcher_json (the settings schema, see the contract doc)."""
    s = env.up.helper.load_launcher_json()
    assert s == {"accounts": {}, "launcher": {
        "ttr-dir": str(env.home / "Toontown Rewritten"),
        "use-stored-accounts": False, "use-password-encryption": False,
        "display-logging": False, "use-os-keyring": True}}
    assert (env.home / "launcher.json").exists()
