#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Checks that this machine can build and test TTR NX2. One line per
# requirement; exits non-zero if any requirement fails. Warnings do not fail.
#   tools/doctor.sh          developer Mac (or Linux workstation)
#   tools/doctor.sh --ci     GitHub Actions: skips workstation-only tools
set -u

ci=0
[ "${1:-}" = "--ci" ] && ci=1
root=$(cd "$(dirname "$0")/.." && pwd)
fails=0
warns=0

pass() { printf 'pass  %-22s %s\n' "$1" "$2"; }
fail() { printf 'FAIL  %-22s %s\n' "$1" "$2"; fails=$((fails + 1)); }
warn() { printf 'warn  %-22s %s\n' "$1" "$2"; warns=$((warns + 1)); }

# tool NAME VERSION-COMMAND [ci]  -- "ci" means also required in CI
tool() {
    local name=$1 cmd=$2 in_ci=${3:-}
    if [ "$ci" = 1 ] && [ "$in_ci" != ci ]; then return; fi
    if command -v "$name" >/dev/null 2>&1; then
        pass "$name" "$(eval "$cmd" 2>&1 | head -n 1)"
    else
        fail "$name" "not found (see docs/dev-setup-macos.md)"
    fi
}

# --- host -------------------------------------------------------------------
arch=$(uname -m)
os=$(uname -s)
case "$arch" in
arm64 | aarch64) pass "cpu" "$os $arch (arm64 containers run natively)" ;;
x86_64) warn "cpu" "$os $arch: arm64 bench containers will be emulated and slow" ;;
*) fail "cpu" "$os $arch is not supported" ;;
esac

if [ "$os" = Darwin ] && [ "$ci" = 0 ]; then
    pass "macos" "$(sw_vers -productVersion)"
    if xcode-select -p >/dev/null 2>&1; then
        pass "xcode-clt" "$(xcode-select -p)"
    else
        fail "xcode-clt" "run: xcode-select --install"
    fi
    tool brew "brew --version"
fi

if [ "$ci" = 0 ]; then
    free_kb=$(df -Pk "$root" | awk 'NR==2 {print $4}')
    free_gb=$((free_kb / 1024 / 1024))
    if [ "$free_gb" -lt 10 ]; then
        fail "disk" "${free_gb} GB free; at least 10 GB needed, 40 GB planned"
    elif [ "$free_gb" -lt 40 ]; then
        warn "disk" "${free_gb} GB free; 40 GB planned for later phases (LKL, rootfs)"
    else
        pass "disk" "${free_gb} GB free"
    fi
fi

# --- tools ------------------------------------------------------------------
tool git "git --version" ci
tool make "make --version" ci
tool docker "docker --version" ci
tool python3.12 "python3.12 --version" ci
tool jq "jq --version" ci
tool shellcheck "shellcheck --version | sed -n 2p" ci
tool gitleaks "gitleaks version" ci
tool xxd "echo present" ci
tool cmake "cmake --version"
tool gh "gh --version"
tool lftp "lftp --version"

if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
        pass "docker-daemon" "$(docker info --format '{{.OperatingSystem}} {{.Architecture}}' 2>/dev/null)"
        if docker buildx version >/dev/null 2>&1; then
            pass "docker-buildx" "$(docker buildx version | head -n 1)"
        else
            fail "docker-buildx" "brew install docker-buildx, then see docs/dev-setup-macos.md"
        fi
        # Colima and Docker Desktop only share folders they are told to share;
        # an unshared folder appears empty in the container and builds fail
        # with "no makefile found".
        img=docker.io/library/debian@sha256:1d04200c2ece1d4d75a2a6f8e11ebce7d86a2ae28b34bb2c9cbb3ee9f4953e75
        if docker run --rm -v "$root:/w:ro" "$img" test -f /w/CLAUDE.md >/dev/null 2>&1; then
            pass "docker-mount" "$root is visible in containers"
        else
            fail "docker-mount" "$root is not shared with the container VM (see docs/dev-setup-macos.md)"
        fi
    else
        fail "docker-daemon" "not running (colima start --vz-rosetta)"
    fi
fi

# --- repository -------------------------------------------------------------
cd "$root" || exit 1
if git rev-parse --git-dir >/dev/null 2>&1; then
    bad=$(git submodule status | grep -E '^[-+U]' || true)
    if [ -z "$(git submodule status)" ]; then
        fail "submodules" "none registered"
    elif [ -n "$bad" ]; then
        fail "submodules" "not at pinned commits: git submodule update --init"
    else
        pass "submodules" "$(git submodule status | wc -l | tr -d ' ') at pinned commits"
    fi
    if [ "$ci" = 0 ]; then
        if [ "$(git config core.hooksPath)" = ".githooks" ]; then
            pass "git-hooks" "core.hooksPath=.githooks"
        else
            fail "git-hooks" "run: make hooks"
        fi
    fi
else
    fail "repository" "$root is not a git checkout"
fi

echo
if [ "$fails" -gt 0 ]; then
    echo "doctor: $fails failed, $warns warning(s)"
    exit 1
fi
echo "doctor: all requirements met, $warns warning(s)"
