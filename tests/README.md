# tests/

- `unit/` — macOS tier, `make test` (unittest cases, run by pytest).
- `launcher/` — launcher contract suite, `make test`: the unmodified Simple
  TTR Launcher against `tools/fake_ttr_api/` (ADR 0004,
  `docs/recon/launcher-contract.md`).
- `bench/` — PC bench tier (Phase 3+).
- `nx2like/` — bench in nx2-like mode enforcing C1–C8 (Phase 3+).
- `toolchain/hello/` — Phase 0 toolchain proof, `make hello`.
