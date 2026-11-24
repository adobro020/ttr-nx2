#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Configures the GitHub project for TTR NX2. Every step is outward-facing, so
# each runs only when named on the command line, after the human approved it
# (CLAUDE.md rule 10):
#   tools/github/setup-project.sh create      private repo + push main
#   tools/github/setup-project.sh labels      phase-NN, gate, hardware-needed, ...
#   tools/github/setup-project.sh milestones  one per phase
#   tools/github/setup-project.sh protect     protect main, require CI
# REPO defaults to <your login>/ttr-nx2.
set -euo pipefail

root=$(cd "$(dirname "$0")/../.." && pwd)
repo=${REPO:-"$(gh api user --jq .login)/ttr-nx2"}

phases=(
    "00:workspace and repo"
    "01:hardware probes"
    "02:reference baselines"
    "03:gx runtime"
    "04:python guest"
    "05:launcher adapter"
    "06:native login ui"
    "07:box64 interpreter"
    "08:display audio input"
    "09:first boot"
    "10:staged jit dynarec"
    "11:playable"
    "12:release"
)

create() {
    # --private is not optional: the repository stays private until gate G8.
    gh repo create "$repo" --private --source "$root" --remote origin \
        --description "Unofficial: Toontown Rewritten on Switch 2 under kaiHEN (not affiliated with Nintendo, Disney or TTR)" \
        --push
    gh repo view "$repo" --json visibility
}

labels() {
    local p
    for p in "${phases[@]}"; do
        gh label create "phase-${p%%:*}" --repo "$repo" --color 1d76db \
            --description "Phase ${p%%:*}: ${p#*:}" --force
    done
    gh label create gate --repo "$repo" --color b60205 --description "Feasibility gate G1-G8" --force
    gh label create hardware-needed --repo "$repo" --color fbca04 --description "Needs the console" --force
    gh label create upstream --repo "$repo" --color 5319e7 --description "Belongs to an upstream project" --force
    gh label create security --repo "$repo" --color d93f0b --description "Secrets, credentials, console safety" --force
    gh label create perf --repo "$repo" --color 0e8a16 --description "Performance" --force
}

milestones() {
    local p existing
    existing=$(gh api "repos/$repo/milestones?state=all&per_page=100" --jq '.[].title')
    for p in "${phases[@]}"; do
        local title="Phase ${p%%:*}: ${p#*:}"
        if ! grep -qxF "$title" <<<"$existing"; then
            gh api "repos/$repo/milestones" -f title="$title" >/dev/null
            echo "milestone: $title"
        fi
    done
}

protect() {
    # Job names from .github/workflows/ci.yml.
    gh api -X PUT "repos/$repo/branches/main/protection" --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "guardrails, lint, unit tests, doctor",
      "build hello.nro (devkit container)"
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
    echo "main protected in $repo"
}

[ $# -gt 0 ] || { sed -n '4,12p' "$0"; exit 2; }
for step in "$@"; do
    case "$step" in
    create | labels | milestones | protect) "$step" ;;
    *) echo "unknown step: $step" >&2; exit 2 ;;
    esac
done
