#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# The human's logged-in reference run (docs/recon/human-run.md). Runs in
# docker/bench-arm64 with networking on and the VNC port published on the
# Mac's loopback only (make human-run). Starts a virtual X server, shares it
# over VNC so the human can see and play the game, then runs the unmodified
# launcher through tools/ref/human_run.py.
set -euo pipefail

mode=${1:-dynarec}
shift || true

export DISPLAY=:99
Xvfb :99 -screen 0 1280x720x24 -nolisten tcp >/tmp/xvfb.log 2>&1 &
for _ in $(seq 50); do xdpyinfo >/dev/null 2>&1 && break; sleep 0.1; done
# Reachable only through the port docker publishes on 127.0.0.1 (Makefile).
# macOS Screen Sharing will not connect to a VNC server without a password,
# so each run gets a fresh throwaway one. It guards only this loopback view
# of the game; it is not a TTR credential. VNC passwords are 8 characters.
vncpw=$(python3.12 -c 'import secrets; print(secrets.token_hex(4))')
x11vnc -storepasswd "$vncpw" /tmp/vncpass >/dev/null 2>&1
x11vnc -display :99 -forever -shared -rfbauth /tmp/vncpass -quiet -rfbport 5900 >/tmp/x11vnc.log 2>&1 &
echo "human-run: open vnc://localhost:5900 in Finder (Go > Connect to Server) to see the game"
echo "human-run: Screen Sharing password for this run: $vncpw (local only, not your TTR password)"
exec python3.12 tools/ref/human_run.py --mode "$mode" "$@"
