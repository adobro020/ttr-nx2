# Launcher contract — Simple TTR Launcher 4.0

What the pinned launcher does at its edges: every terminal I/O call site, the
settings it keeps, the files it writes, the network calls it makes and the
exact game launch. This is the specification the Phase 5 adapter implements
from outside the (unmodified) source. Line numbers are at
`third_party/Simple-TTR-Launcher` commit
`af80b26bbf06cbd9d25c53b225003bd310c00252` (tag 4.0). Behaviour marked
**tested** is exercised by `tests/launcher/` (`make test`) against
`tools/fake_ttr_api/`.

## 1. Module structure

| File | Role | Import side effects |
|---|---|---|
| `main.py` | text menu, `main()` | **calls `main()` at import** (line 208); never import it |
| `launcher.py` | `Launcher`: accounts, login, 2FA/ToonGuard, queue, start game | none |
| `patcher.py` | `Patcher`: mirrors, manifest, SHA-1 checks, bz2, bsdiff | none (`Patcher()` itself fetches the mirrors list) |
| `encrypt.py` | `Encrypt`: Argon2id (t=3, m=65536 KiB, p=4) + Fernet | none |
| `helper.py` | settings JSON, keyring, `retry`, `confirm`, `clear`, `quit_launcher` | imports `keyring`; imports `winreg` on Windows only |

Entry points the adapter calls: `Launcher()` (loads settings, may prompt, see
§3), `Launcher.prepare_login()`, `add_account()`, `change_account()`,
`remove_account()`, `change_ttr_dir()`, `manage_password_encryption()`,
`toggle_account_storage()`, `toggle_os_keyring()`, `toggle_game_log_display()`.

`sys.argv` is read: `len(sys.argv) == 2` makes `prepare_login()` use
`sys.argv[1]` as the stored-account number (launcher.py:482-492);
`len(sys.argv) == 3` suppresses the "encryption is not enabled" warning
(launcher.py:38). The adapter must set `sys.argv` deliberately (tests use
`["main.py"]`).

## 2. Terminal I/O call sites

Kinds: `input` = builtin `input()`; `pwinput` = `pwinput.pwinput()` (masked);
`confirm` = `helper.confirm(text, lo, hi)`, which loops on `int(input(text))`
printing `Invalid choice. Try again.` until the value is in range
(helper.py:144-164, **tested**); `print-prompt` = a `print` whose text is the
question or the context for the next input.

### `input` and `pwinput`

| File:line | Function | Prompt (exact) | Answer |
|---|---|---|---|
| helper.py:154 | `confirm` | (caller's text) | integer in [lo, hi] |
| helper.py:173 | `quit_launcher` | `Press enter to quit.` | anything; then `sys.exit(ret)` |
| launcher.py:166 | `__check_additional_auth` | `Enter token: ` | 2FA or ToonGuard token; `rstrip()`ped (**tested**) |
| launcher.py:303 | `add_account` | `Enter username to store or 0 to cancel: ` | username, or `0` (any all-decimal string equal to 0) to cancel |
| launcher.py:309 | `add_account` | `Enter password to store: ` (pwinput) | password |
| launcher.py:378 | `change_account` | `Enter new password: ` (pwinput) | password |
| launcher.py:534 | `prepare_login` (storage off) | `Enter username: ` | username (**tested**) |
| launcher.py:535 | `prepare_login` (storage off) | `Enter password: ` (pwinput) | password (**tested**) |
| launcher.py:546 | `change_ttr_dir` | `Enter your desired installation path or 0 to cancel: ` | path (`expanduser` applied) or `0` |
| encrypt.py:262 | `manage_password_encryption` | `Create a master password: ` (pwinput) | new master password, no confirmation (**tested**) |
| encrypt.py:445 | `verify_master_password` | `Enter your master password: ` (pwinput) | master password; 3 wrong → `False` (**tested**) |

### `confirm`

| File:line | Function | Prompt | Range |
|---|---|---|---|
| main.py:66 | `show_menu` | `Choose an option: ` | 1–9 |
| main.py:162 | `show_options_menu` | `Choose an option or enter 0 to return: ` | 0–5 |
| launcher.py:372 | `change_account` | `Enter account number or 0 to cancel: ` | 0–n |
| launcher.py:434 | `remove_account` | `Enter account number or 0 to cancel: ` | 0–n |
| launcher.py:501 | `prepare_login` (n > 1 stored) | `Enter account number or 0 to cancel: ` | 0–n (**tested**, incl. invalid answers) |
| launcher.py:596 | `toggle_os_keyring` | `Enter 1 to confirm or 0 to cancel: ` | 0–1 |
| patcher.py:75 | `__check_install_path` | `Enter 1 to confirm or 0 to cancel: ` | 0–1 (**tested**, both answers) |
| encrypt.py:233 | `manage_password_encryption` (disable) | `Enter 1 to confirm or 0 to cancel: ` | 0–1 (**tested**) |

### `print-prompt` (context printed right before an answer is needed)

| File:line | Text | Followed by |
|---|---|---|
| launcher.py:165 | the API's `banner` (e.g. "Please enter an authenticator token.") | `Enter token: ` |
| launcher.py:366-370 | `Which account do you wish to modify?` + numbered usernames | confirm 372 |
| launcher.py:427-432 | `Which account do you wish to delete?` + list | confirm 434 |
| launcher.py:494-499 | `Which account do you wish to log in?` + list | confirm 501 |
| launcher.py:544 | `Current installation path: {cur}` | input 546 |
| launcher.py:590-594 | `You are currently storing at least one account. …` | confirm 596 |
| patcher.py:74 | `The path {abs} does not exist. Create it?` | confirm 75 |
| encrypt.py:229-232 | `Would you like to remove password encryption?` + warning | confirm 233 |
| encrypt.py:254-259 | `You can use a master password to encrypt …` | pwinput 262 |
| encrypt.py:34-36, 386-388 | `To improve security your passwords will need to be re-encrypted.` | pwinput 445 |
| main.py:48-62, 147-160 | box-drawn menus | confirm 66 / 162 |

Status-only prints the adapter turns into status messages (not prompts):
`Requesting login...` (launcher.py:133), banners on failure (141, 178, 219),
fixed failure texts (143-146, 180-183, 221-223, 88-91), `You are queued in
position {n}.` (206), `Login successful!` (234), `Login failed!` (293),
`Retrying...` (helper.py:202, 210), patcher failures (patcher.py:40-48,
111-121, 130-132, 387-389, 392, 514, 548), account messages (342, 411, 456,
363, 424), keyring failures (helper.py:238-293), settings errors (helper.py:65,
70, 88; encrypt.py:356-359).

### `clear`, `webbrowser`, `tqdm`, `subprocess`

| File:line | Call | Note |
|---|---|---|
| helper.py:220-226 | `clear()` → `os.system('clear')` (`cls` on win32) | `os.system` forks: impossible under gx (C7). Replace `helper.clear`. |
| main.py:109, 166, 170, 174, 178, 183, 188 | `helper.clear()` | menu only |
| main.py:83, 87, 91, 95 | `webbrowser.open(url)` for toon.town, toon.town/status, toontownrewritten.wiki, toonhq.org | menu only; the adapter does not offer these |
| patcher.py:16 | `from tqdm.auto import tqdm` | module-level name `patcher.tqdm` |
| patcher.py:445-450 | `tqdm.wrapattr(comp_file, 'write', total=Content-Length, unit='B', unit_scale=True, desc=f'Downloading {local_filename}', leave=False, ascii=' █')` | one per download, from worker threads |
| patcher.py:498-501 | `tqdm(total=compressed size, unit='B', unit_scale=True, desc=f'Decompressing {filename}', leave=False, ascii=' █')`; `pbar.update(len(data))` | totals compressed size but counts decompressed bytes |
| launcher.py:267-272 | `subprocess.Popen(args=process, cwd, stdout, stderr, creationflags)` | Windows only |
| launcher.py:284 | `subprocess.run(args=process, cwd=ttr_dir, check=False)` | Linux/macOS, `display-logging` on (**tested**) |
| launcher.py:286-288 | `subprocess.Popen(args=process, cwd=ttr_dir, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, start_new_session=True)` | Linux/macOS default (**tested**) |

There is no `thread_map` in 4.0 (the architecture document's list came from
`master`); downloads use a `concurrent.futures.ThreadPoolExecutor` with
`max_workers=os.cpu_count()` (patcher.py:377).

## 3. The game launch (launcher.py:228-288)

1. `print('\nLogin successful!')`.
2. `os.environ['TTR_GAMESERVER'] = resp['gameserver']` and
   `os.environ['TTR_PLAYCOOKIE'] = resp['cookie']` — **in the launcher's own
   process environment** (lines 244-245), inherited by the child.
3. `platform.system()` picks the binary: `'Linux'` → `TTREngine`,
   `'Darwin'` → `Toontown Rewritten`, Windows → `TTREngine64`/`TTREngine`.
4. `process = os.path.join(ttr_dir, binary)`; `os.chmod(process, mode | 0o111)`
   (line 281). A missing file raises `FileNotFoundError`, caught at line 101:
   `Could not find Toontown Rewritten. …` (**tested**).
5. `args` is the **path string**, not a list; `cwd=ttr_dir`. With
   `display-logging` off: `Popen(..., stdout=DEVNULL, stderr=STDOUT,
   start_new_session=True)`; on: `run(..., check=False)` (blocks until the
   game exits). Recorded keyword arguments, **tested** exactly:

   ```
   Popen(args='<ttr-dir>/TTREngine', cwd='<ttr-dir>',
         stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
         start_new_session=True)
   ```

For gx (no fork/exec, C7) the adapter replaces `subprocess.Popen`/`run` for
this one call with `os.execve(box64, [box64, process], env)` where `env`
carries the two variables; the cookie then exists only in memory
(architecture decision 3). Note the engine's own reaction to a missing cookie
(Phase 2 run, `docs/recon/engine-91bff107.md`): it prints "please log in using
the official launcher" and exits.

## 4. Network calls and cadence

All HTTPS with certificate verification (requests defaults), timeout 30 s.

| Call | Where | Retry |
|---|---|---|
| `POST https://www.toontownrewritten.com/api/login?format=json`, form `username`,`password`; header `Content-type: application/x-www-form-urlencoded` | launcher.py:65-67, 116 | `helper.retry(3, 5, …)`: 3 attempts, 5 s apart (**tested**: 2 failures then success; 3 failures → "Could not connect …") |
| same, form `appToken` (rstripped), `authToken` (= last `responseToken`) | launcher.py:167-172 | same |
| same, form `queueToken`; after `sleep(max(eta, 1))` | launcher.py:201-213 | same; **requires `queueToken` in every delayed response** (KeyError otherwise) although api-doc's example update omits it |
| `GET https://www.toontownrewritten.com/api/mirrors` (Session) → JSON list, shuffled | patcher.py:56-63, in `Patcher.__init__` | `retry(3, 10)`; failure leaves `mirrors=None` and any later download fails (**tested**) |
| `GET https://cdn.toontownrewritten.com{manifest}` (`.txt` appended if the path ends in `patchmanifest`) | patcher.py:162-171 | `retry(3, 10)` (**tested**) |
| `GET urljoin(mirror, <remote name>)`, streamed, 64 KiB chunks | patcher.py:436-454 | per file `retry(3, 10)`; on HTTP/connection error the mirror is removed from the shared list if more than one is left (**tested**) |

Upstream quirks found by the tests (behaviour to design around, not to fix):

- **Unreachable "Could not decode" branch.** With requests ≥ 2.27,
  `Response.json()` raises `requests.exceptions.JSONDecodeError`, a subclass
  of `RequestException`, so a non-JSON manifest is retried and reported as
  "Could not download the patch manifest" (patcher.py:110 catches it first).
  Same for the login (launcher.py:87) and mirrors (patcher.py:39). **Tested.**
- **Mirror-removal race.** `if len(mirrors) > 1: mirrors.remove(mirror)`
  (patcher.py:475-476) runs in several worker threads at once; two threads
  failing on the same mirror can both pass the check, and the second
  `remove` raises `ValueError`, which escapes `future.result()`
  (patcher.py:386) and out of `check_update`. The failover test pins
  `os.cpu_count()` to 1.
- Bytes are hashed with SHA-1 throughout (`hash`, `compHash`, `patchHash`,
  `compPatchHash`); a mismatch fails that download, which is retried 3 times
  (**tested** for compressed, decompressed and post-patch mismatches).

## 5. Settings schema (`launcher.json`)

Written with `json.dump(..., indent=4)` (helper.py:85-86). Created on first
`load_launcher_json()` with (helper.py:47-57, **tested**):

```json
{"accounts": {},
 "launcher": {"ttr-dir": "<launcher dir>/Toontown Rewritten",
              "use-stored-accounts": false,
              "use-password-encryption": false,
              "display-logging": false,
              "use-os-keyring": true}}
```

Keys added later: `launcher.hashing-params` `{"t": 3, "m": 65536, "p": 4}`,
`launcher.salt-verification` (urlsafe base64, 16 bytes),
`launcher.password-verification` (Fernet token of the verification salt);
legacy `launcher.password-salt` triggers re-encryption (encrypt.py:33-60).
Accounts are `accounts.account1..n`: `{"username", "password", "salt"?}`
where `password` is plaintext, a Fernet token (encryption on), or
`KEYRING_PASS` (keyring on; the keyring then holds the plaintext or the
Fernet token). Numbering is renumbered on removal (launcher.py:450-453).
`fix_settings_data` (helper.py:92-127) adds missing keys and expands a
leading `~` in `ttr-dir`.

Turning on account storage with the keyring off and encryption off forces
master-password creation (launcher.py:577-579, **tested**).

## 6. Files written

| Path | By | Note |
|---|---|---|
| `<get_launcher_path()>/launcher.json` | helper.py:84-86 | **next to `helper.py`** (the source directory) unless frozen. On the console the rootfs is read-only: the adapter must replace `helper.get_launcher_path` (the tests do) to point under `sdmc:/switch/ttr-nx2/data/`. |
| `./login.json` → `./launcher.json` | helper.py:24-25 | legacy rename, **relative to the current directory** |
| `<ttr-dir>/` | patcher.py:80 | created after confirm |
| `<ttr-dir>/tmpXXXX/` | patcher.py:364 | `tempfile.TemporaryDirectory(dir=ttr_dir)`; compressed downloads and decompressed files staged here, removed afterwards (**tested**) |
| `<ttr-dir>/<file>` | patcher.py:537 (`shutil.move`) / 540 (`bsdiff4.file_patch_inplace`) | full files moved in; patches applied in place |
| `<ttr-dir>/TTREngine` mode | launcher.py:281 | `+x` for user, group, other |
| OS keyring, service `Simple-TTR-Launcher` | helper.py:236, 260, 287 | only with `use-os-keyring` |

The game itself writes into its install directory too (logs, settings); see
the engine recon document.

## 7. Secrets in the launcher's own output

The tests check that no password, master password, token, queue token or
cookie appears in anything the launcher prints during any scenario. The
launcher prints API `banner` strings verbatim. It never prints the cookie;
it does put it in `os.environ` (§3), so anything that dumps the environment
of the launcher process or the game (for example `strace -v`, `/proc/*/environ`
or a crash reporter) can leak it.
