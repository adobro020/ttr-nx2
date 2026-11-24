# 0003 — Guard rails: one checker, run by the hook and by CI

Date: 2026-11-24. Status: accepted (Phase 0).

## Context

Rules 1, 3 and 4 (no game files, launcher untouched, no secrets) must hold
for every commit, including commits made with `--no-verify` and files added
then removed inside a pull request.

## Options

1. gitleaks alone with custom rules. Cannot check submodule pins or sizes.
2. The `pre-commit` framework. Adds a Python dependency and network fetches
   of hook repositories.
3. A small stdlib-only checker (`tools/guardrails/check.py`) plus gitleaks,
   invoked from a plain git hook and from CI.

## Decision

Option 3. The checker has three modes over the same rules: `--staged` (hook),
`--all` (CI, tree at HEAD) and `--history RANGE` (CI, every blob any commit
added). Rules: blobs over 5 MB; basenames matching `TTREngine*` or `*.mf`
(case-insensitive); the launcher gitlink, `third_party/launcher.pin` and the
checked-out launcher tree must agree and be clean; any line assigning a
value to `TTR_PLAYCOOKIE`. gitleaks (default rules plus the same cookie rule
in `.gitleaks.toml`) runs in both places. `.gitignore` is a third layer.

## Consequences

- A bypassed hook only moves the failure to CI, which scans full history.
- Findings never echo the matched value.
- The cookie rule has a per-path allowlist (`tools/guardrails/cookie-allowlist.txt`,
  mirrored in `.gitleaks.toml`); currently only the Phase 0 brief, which
  quotes the dummy test value. Every entry needs a reason.
- Placeholders (`<value>`, `$VAR`, `{var}`, `[REDACTED]`, `***`) and code that
  sets the variable from a variable do not match, so the adapter can be
  written normally.
