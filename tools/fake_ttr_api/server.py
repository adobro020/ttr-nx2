# SPDX-License-Identifier: GPL-2.0-only
"""A local HTTPS stand-in for TTR's login API, mirrors list, patch manifest
and download mirrors, so the unmodified launcher can be exercised without
touching TTR's servers (CLAUDE.md rule 5).

Behaviour follows ToontownRewritten/api-doc ``login.md`` (commit recorded in
docs/upstream-notes.md) and how the pinned launcher calls it
(``launcher.py``: ``__check_login_info``, ``__check_additional_auth``,
``__check_queue``; ``patcher.py``: ``__get_mirrors``,
``__get_patch_manifest``, ``__download_file``). Every login value is a
string, as the API document states.

One server answers for every host name; requests are told apart by the Host
header. ``tools.fake_ttr_api.redirect`` sends the launcher's connections for
the real host names here at the socket layer.
"""

from __future__ import annotations

import json
import secrets
import ssl
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .certs import CertFiles, make_certs
from .fixtures import GameFixture

LOGIN_HOST = "www.toontownrewritten.com"
CDN_HOST = "cdn.toontownrewritten.com"
MIRROR_HOSTS = ("mirror-a.fake-ttr.test", "mirror-b.fake-ttr.test")
HOSTS = (LOGIN_HOST, CDN_HOST, *MIRROR_HOSTS)
MANIFEST_PATH = "/content/patchmanifest.txt"
GAMESERVER = "gameserver.fake-ttr.test"

# Login scenarios. Each is a script of (expected request kind, response).
# Kinds: "credentials" (username+password), "token" (appToken+authToken),
# "queue" (queueToken). Responses may name tokens as {t1}, {q1}: they are
# filled with fresh random values per server so tests can check the launcher
# echoes them back.
SCENARIOS: dict[str, list[tuple[str, dict[str, str]]]] = {
    "success": [
        ("credentials", {"success": "true"}),
    ],
    "failure": [
        ("credentials", {"success": "false",
                         "banner": "Fake: incorrect username or password."}),
    ],
    "failure_no_banner": [
        ("credentials", {"success": "false"}),
    ],
    "partial": [
        ("credentials", {"success": "partial",
                         "banner": "Fake: please enter an authenticator token.",
                         "responseToken": "{t1}"}),
        ("token", {"success": "partial",
                   "banner": "Fake: please enter a ToonGuard code.",
                   "responseToken": "{t2}"}),
        ("token", {"success": "true"}),
    ],
    "partial_rejected": [
        ("credentials", {"success": "partial",
                         "banner": "Fake: please enter an authenticator token.",
                         "responseToken": "{t1}"}),
        ("token", {"success": "false",
                   "banner": "Fake: too many token attempts."}),
    ],
    "queue": [
        ("credentials", {"success": "delayed", "eta": "0", "position": "3",
                         "queueToken": "{q1}"}),
        ("queue", {"success": "delayed", "eta": "2", "position": "2",
                   "queueToken": "{q1}"}),
        ("queue", {"success": "delayed", "eta": "1", "position": "1",
                   "queueToken": "{q1}"}),
        ("queue", {"success": "true"}),
    ],
    "queue_failure": [
        ("credentials", {"success": "delayed", "eta": "1", "position": "9",
                         "queueToken": "{q1}"}),
        ("queue", {"success": "false",
                   "banner": "Fake: the queue closed."}),
    ],
}


@dataclass
class Request:
    host: str
    method: str
    path: str
    query: dict[str, list[str]]
    form: dict[str, str]
    headers: dict[str, str]


@dataclass
class Faults:
    """Failures to inject, all off by default."""
    login_http_errors: int = 0          # first N login POSTs get HTTP 500
    mirrors_http_errors: int = 0        # first N mirror-list GETs get HTTP 500
    manifest_http_errors: int = 0       # first N manifest GETs get HTTP 500
    manifest_not_json: bool = False
    down_hosts: set[str] = field(default_factory=set)       # always HTTP 503
    corrupt_downloads: set[str] = field(default_factory=set)  # remote names


class FakeTTR:
    """Run with ``with FakeTTR(tmpdir) as fake: ...``; ``fake.port`` is the
    local port, ``fake.requests`` every request seen, ``fake.errors`` any
    request the scenario did not expect."""

    def __init__(self, workdir: Path, scenario: str = "success",
                 fixture: GameFixture | None = None,
                 faults: Faults | None = None) -> None:
        if scenario not in SCENARIOS:
            raise ValueError(f"unknown scenario {scenario!r}")
        self.scenario = scenario
        self.fixture = fixture or GameFixture.build()
        self.faults = faults or Faults()
        self.certs: CertFiles = make_certs(workdir / "certs", list(HOSTS))
        self.cookie = "fakecookie-" + secrets.token_hex(16)
        self.tokens = {k: f"fake-{k}-" + secrets.token_hex(8)
                       for k in ("t1", "t2", "q1")}
        self.requests: list[Request] = []
        self.errors: list[str] = []
        self._step = 0
        self._counts: dict[str, int] = {}
        self._lock = threading.Lock()
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    # -- lifecycle -----------------------------------------------------------
    @property
    def port(self) -> int:
        assert self._httpd is not None
        return self._httpd.server_address[1]

    def start(self) -> "FakeTTR":
        handler = type("Handler", (_Handler,), {"fake": self})
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(self.certs.cert_pem, self.certs.key_pem)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        httpd.daemon_threads = True
        self._httpd = httpd
        self._thread = threading.Thread(target=httpd.serve_forever,
                                        name="fake-ttr-api", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread:
            self._thread.join(timeout=5)

    def __enter__(self) -> "FakeTTR":
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    # -- helpers for tests -----------------------------------------------------
    def requests_to(self, host: str, path: str | None = None) -> list[Request]:
        return [r for r in self.requests
                if r.host == host and (path is None or r.path == path)]

    def downloaded(self) -> list[str]:
        """Remote file names fetched from any mirror (successfully or not)."""
        return [r.path.rsplit("/", 1)[-1] for r in self.requests
                if r.host in MIRROR_HOSTS]

    def login_done(self) -> bool:
        return self._step >= len(SCENARIOS[self.scenario])

    # -- request handling (called from server threads) -------------------------
    def _count(self, key: str) -> int:
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    def handle(self, req: Request) -> tuple[int, str, bytes]:
        with self._lock:
            self.requests.append(req)
            if req.host in self.faults.down_hosts:
                return 503, "text/plain", b"fake: host down\n"
            if req.host == LOGIN_HOST and req.path == "/api/login":
                return self._login(req)
            if req.host == LOGIN_HOST and req.path == "/api/mirrors":
                if self._count("mirrors") <= self.faults.mirrors_http_errors:
                    return 500, "text/plain", b"fake: error\n"
                mirrors = [f"https://{h}/patches/" for h in MIRROR_HOSTS]
                return 200, "application/json", json.dumps(mirrors).encode()
            if req.host == CDN_HOST and req.path == MANIFEST_PATH:
                if self._count("manifest") <= self.faults.manifest_http_errors:
                    return 500, "text/plain", b"fake: error\n"
                if self.faults.manifest_not_json:
                    return 200, "text/plain", b"<html>not json</html>"
                body = json.dumps(self.fixture.manifest).encode()
                return 200, "application/json", body
            if req.host in MIRROR_HOSTS and req.path.startswith("/patches/"):
                name = req.path[len("/patches/"):]
                data = self.fixture.downloads.get(name)
                if data is None:
                    return 404, "text/plain", b"fake: not found\n"
                if name in self.faults.corrupt_downloads:
                    data = data[:-1] + bytes([data[-1] ^ 0xFF])
                return 200, "application/octet-stream", data
            self.errors.append(f"unexpected {req.method} {req.host}{req.path}")
            return 404, "text/plain", b"fake: unknown endpoint\n"

    def _login(self, req: Request) -> tuple[int, str, bytes]:
        if req.method != "POST":
            self.errors.append(f"login with {req.method}")
            return 405, "text/plain", b""
        if req.query.get("format") != ["json"]:
            self.errors.append(f"login without format=json: {req.query}")
        ctype = req.headers.get("content-type", "")
        if not ctype.startswith("application/x-www-form-urlencoded"):
            self.errors.append(f"login content-type {ctype!r}")
        if self._count("login") <= self.faults.login_http_errors:
            return 500, "text/plain", b"fake: error\n"

        script = SCENARIOS[self.scenario]
        if self._step >= len(script):
            self.errors.append("login request after the scenario ended")
            return 200, "application/json", json.dumps(
                {"success": "false", "banner": "fake: scenario over"}).encode()
        kind, response = script[self._step]
        problem = self._check_kind(kind, req.form)
        if problem:
            self.errors.append(f"step {self._step}: {problem}")
            return 200, "application/json", json.dumps(
                {"success": "false", "banner": f"fake: {problem}"}).encode()
        self._step += 1
        body = {k: v.format(**self.tokens) for k, v in response.items()}
        if body["success"] == "true":
            body.update(gameserver=GAMESERVER, cookie=self.cookie,
                        manifest=MANIFEST_PATH)
        return 200, "application/json", json.dumps(body).encode()

    def _check_kind(self, kind: str, form: dict[str, str]) -> str | None:
        keys = set(form)
        if kind == "credentials":
            if keys != {"username", "password"}:
                return f"expected username+password, got {sorted(keys)}"
        elif kind == "token":
            if keys != {"appToken", "authToken"}:
                return f"expected appToken+authToken, got {sorted(keys)}"
            # The launcher must echo the most recent responseToken.
            expected = self.tokens["t2"] if self._step >= 2 else self.tokens["t1"]
            if form["authToken"] != expected:
                return "authToken is not the last responseToken"
        elif kind == "queue":
            if keys != {"queueToken"}:
                return f"expected queueToken, got {sorted(keys)}"
            if form["queueToken"] != self.tokens["q1"]:
                return "queueToken does not match"
        return None


class _Handler(BaseHTTPRequestHandler):
    fake: FakeTTR
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        # Silent: request bodies carry (fake) passwords; never log them.
        pass

    def _serve(self) -> None:
        split = urlsplit(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        form = {k: v[0] for k, v in parse_qs(raw.decode(),
                                             keep_blank_values=True).items()}
        host = (self.headers.get("Host") or "").split(":")[0]
        req = Request(host=host, method=self.command, path=split.path,
                      query=parse_qs(split.query), form=form,
                      headers={k.lower(): v for k, v in self.headers.items()})
        status, ctype, body = self.fake.handle(req)
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = _serve
    do_POST = _serve
