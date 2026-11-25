# SPDX-License-Identifier: GPL-2.0-only
"""Run the fake TTR API standalone, for manual checks of an adapter.

Prints the port and the CA file. Point a client at it by resolving the TTR
host names to 127.0.0.1 and that port, trusting the CA (REQUESTS_CA_BUNDLE).
"""

from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path

from .server import HOSTS, SCENARIOS, FakeTTR


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scenario", default="success", choices=sorted(SCENARIOS))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp, \
            FakeTTR(Path(tmp), args.scenario) as fake:
        print(f"fake TTR API: scenario={args.scenario} port={fake.port}")
        print(f"hosts: {', '.join(HOSTS)}")
        print(f"CA: {fake.certs.ca_pem}")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
