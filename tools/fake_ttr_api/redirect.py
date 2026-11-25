# SPDX-License-Identifier: GPL-2.0-only
"""Send the launcher's HTTPS connections to the fake server at the socket layer.

``requests`` opens sockets through ``urllib3.util.connection.create_connection``.
Replacing that one function maps (host, 443) for the fake's host names to
127.0.0.1:<fake port> and refuses every other destination, so a test can
never reach the real TTR servers by accident (CLAUDE.md rule 5). TLS still
runs end to end with the real host name for SNI and certificate checks; the
test CA is trusted through REQUESTS_CA_BUNDLE.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator

import urllib3.util.connection as u3conn

PROXY_VARS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy",
              "https_proxy", "all_proxy")


class BlockedConnection(OSError):
    """A test tried to connect somewhere other than the fake server."""


@contextlib.contextmanager
def redirect_hosts(hosts: dict[str, int], ca_bundle: str,
                   closed: set[str] = frozenset()) -> Iterator[list[str]]:
    """Map each name in ``hosts`` to 127.0.0.1:<port>. Names in ``closed``
    get a refused connection (a network failure, not an HTTP error).
    Yields the list of "host:port" destinations the code asked for."""
    original = u3conn.create_connection
    asked: list[str] = []

    def create_connection(address, *args, **kwargs):  # type: ignore[no-untyped-def]
        host, port = address
        asked.append(f"{host}:{port}")
        if host in closed:
            raise ConnectionRefusedError(f"fake: {host} refused")
        if host in hosts and port == 443:
            return original(("127.0.0.1", hosts[host]), *args, **kwargs)
        raise BlockedConnection(f"test blocked a connection to {host}:{port}")

    saved_env = {k: os.environ.get(k) for k in (*PROXY_VARS, "NO_PROXY",
                                                "REQUESTS_CA_BUNDLE")}
    for k in PROXY_VARS:
        os.environ.pop(k, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["REQUESTS_CA_BUNDLE"] = ca_bundle
    u3conn.create_connection = create_connection
    try:
        yield asked
    finally:
        u3conn.create_connection = original
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
