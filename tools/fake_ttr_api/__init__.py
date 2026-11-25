# SPDX-License-Identifier: GPL-2.0-only
"""Fake TTR login API, mirrors, patch manifest and download mirrors for tests.

    from tools.fake_ttr_api import FakeTTR, Faults, redirect_hosts
    with FakeTTR(tmp, scenario="partial") as fake, \\
         redirect_hosts({h: fake.port for h in HOSTS}, str(fake.certs.ca_pem)):
        ...  # run the unmodified launcher code

``python -m tools.fake_ttr_api --scenario queue`` runs it standalone.
"""

from .fixtures import GameFixture
from .redirect import BlockedConnection, redirect_hosts
from .server import (CDN_HOST, HOSTS, LOGIN_HOST, MANIFEST_PATH, MIRROR_HOSTS,
                     SCENARIOS, FakeTTR, Faults)

__all__ = ["BlockedConnection", "CDN_HOST", "FakeTTR", "Faults", "GameFixture",
           "HOSTS", "LOGIN_HOST", "MANIFEST_PATH", "MIRROR_HOSTS", "SCENARIOS",
           "redirect_hosts"]
