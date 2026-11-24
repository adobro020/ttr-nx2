#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Clones upstream sources that are read, never built from or shipped, into
# third_party/reference/ (gitignored), at the commits recorded in
# docs/upstream-notes.md. These are the versions the pinned devkit packages
# were built from. Set FULL=1 to include OunceVK (a Mesa tree, ~500 MB).
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
dest="$root/third_party/reference"
mkdir -p "$dest"

# name  url  commit
refs=(
    "ounce-devkit   https://github.com/ouncebrew/ounce-devkit   5e957599bd498643d82e5470aec80da67a12685d"
    "ounce-pacman   https://github.com/ouncebrew/pacman         6f73dae534b91d16458ef1b8c60c86505824572e"
    "kaihen         https://github.com/ouncebrew/kaihen         3695f364f9270686aa72cc39627bb1281752b2d3"
    "libounce       https://github.com/ouncebrew/libounce       7270a6acee972acf628c482e577b53c7e6f02e76"
    "ounce-examples https://github.com/ouncebrew/ounce-examples 3856a475f0f31e58241cec8985a12838e746d96d"
)
if [ "${FULL:-0}" = 1 ]; then
    refs+=("ouncevk        https://github.com/ouncebrew/ouncevk        06d7dbdf8346325a171c117bf29414724f10a8b2")
fi

for line in "${refs[@]}"; do
    read -r name url commit <<<"$line"
    dir="$dest/$name"
    if [ ! -d "$dir/.git" ]; then
        git init -q "$dir"
        git -C "$dir" remote add origin "$url"
    fi
    git -C "$dir" fetch -q --depth 1 origin "$commit"
    git -C "$dir" -c advice.detachedHead=false checkout -q "$commit"
    echo "$name $(git -C "$dir" rev-parse HEAD)"
done
