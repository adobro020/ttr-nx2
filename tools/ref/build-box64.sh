#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Stock Box64 at the pinned submodule tag, generic ARM64 with the ARM dynarec,
# built out of tree into build/box64-bench/ (Phase 2, step 7). Runs in
# docker/bench-arm64 (make box64-bench). The install is staged under
# build/box64-bench/stage/ instead of /: the container is thrown away after
# each run, so tools/ref/run-engine.sh points Box64 at the staged rc file and
# x86-64 helper libraries with BOX64_RCFILE and BOX64_LD_LIBRARY_PATH.
set -euo pipefail

src=third_party/box64
bld=build/box64-bench
[ -f "$src/CMakeLists.txt" ] || { echo "build-box64: $src missing (git submodule update --init)" >&2; exit 1; }

# The submodule's .git is a gitfile into the superproject; Box64's CMake runs
# git for its version string, which needs the mount to be a safe directory.
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='*'

if [ ! -f "$bld/build.ninja" ]; then
    cmake -S "$src" -B "$bld" -G Ninja \
        -D ARM64=ON -D ARM_DYNAREC=ON -D CMAKE_BUILD_TYPE=RelWithDebInfo
fi
cmake --build "$bld" -j"$(nproc)"
DESTDIR="$PWD/$bld/stage" cmake --install "$bld" >/dev/null
"$bld/box64" --version
echo "build-box64: $bld/box64 and $bld/stage/ ready"
