#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Static reconnaissance of TTREngine and the shared objects shipped beside it
# (Phase 2, step 5). Runs in docker/ref-amd64 (make recon-static). Writes
# plain-text facts to OUT (under build/, git-ignored): headers, program
# headers, dynamic sections, relocation type counts, undefined symbols by
# providing library, library names found as strings. No disassembly and no
# copies of game data are produced (CLAUDE.md rules 1 and docs/recon/README).
set -euo pipefail

game=${1:?usage: recon-static.sh GAME_DIR OUT_DIR}
out=${2:?usage: recon-static.sh GAME_DIR OUT_DIR}
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$out"

elfs=()
for f in "$game"/*; do
    [ -f "$f" ] || continue
    if [ "$(head -c 4 "$f" | od -An -c | tr -d ' ')" = '177ELF' ]; then
        elfs+=("$f")
    fi
done
[ "${#elfs[@]}" -gt 0 ] || { echo "recon-static: no ELF files in $game" >&2; exit 1; }

for f in "${elfs[@]}"; do
    name=$(basename "$f")
    o="$out/$name"
    {
        echo "## sha1"; sha1sum "$f" | cut -d' ' -f1
        echo "## size"; stat -c %s "$f"
        echo "## file"; file -b "$f"
        echo "## readelf -h"; readelf -h "$f"
        echo "## readelf -lW"; readelf -lW "$f"
        echo "## readelf -dW"; readelf -dW "$f"
        echo "## readelf -SW"; readelf -SW "$f"
        echo "## readelf -V (version needs)"; readelf -V "$f" | sed -n '/Version needs section/,$p'
        echo "## relocation types (count type)"
        readelf -rW "$f" | awk '/R_X86_64_/ {c[$3]++} END {for (k in c) print c[k], k}' | sort -rn
        echo "## textrel / static TLS flags"
        readelf -dW "$f" | grep -E 'TEXTREL|FLAGS' || echo "(none)"
        echo "## TLS segment"
        readelf -lW "$f" | grep -E '^\s+TLS' || echo "(none)"
        echo "## GNU_STACK"
        readelf -lW "$f" | grep -E 'GNU_STACK' || echo "(none)"
        echo "## library names appearing as strings (dlopen candidates)"
        strings -a "$f" | grep -E '^lib[A-Za-z0-9_+.-]+\.so(\.[0-9]+)*$' | sort -u || true
        echo "## undefined dynamic symbols by providing library"
        python3 "$here/imports_by_lib.py" "$f"
    } > "$o.txt"
    echo "recon-static: wrote $o.txt"
done
