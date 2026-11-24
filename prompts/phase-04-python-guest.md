# Phase 4 — ARM64 Linux Python 3.12 as a guest

Read `CLAUDE.md`, `docs/ARCHITECTURE.md` and `docs/STATUS.md` first.
Depends on Phase 3. Decides gate **G4**.

## Goal

Stock CPython 3.12 for aarch64 Linux, with the launcher's stock dependencies,
runs on gx on the bench, in nx2-like mode and on the console, and can make an
HTTPS request and do the launcher's cryptography.

## Work

1. **Root filesystem build** (`rootfs/build.sh`, run in `docker/bench-arm64`,
   reproducible with `SOURCE_DATE_EPOCH`):
   - a minimal Debian 12 arm64 base (glibc, `ld.so`, CA certificates, zlib,
     bzip2, the libraries Python needs), built with `mmdebstrap`; record the
     package list and versions for licence compliance;
   - CPython 3.12 for `aarch64-unknown-linux-gnu` from a pinned
     python-build-standalone release, verified by SHA-256, at `/opt/python`;
     if you choose a distribution package of 3.12 instead, justify it in an
     ADR;
   - wheels for `requests`, `cryptography`, `bsdiff4`, `keyring`, `pwinput`,
     `tqdm` and their dependencies, for `cp312` `manylinux` aarch64, resolved
     to a lock file with hashes and installed with `--require-hashes
     --only-binary=:all:`; if any package has no aarch64 wheel, build it in
     the container and record how;
   - bytecode precompiled at build time; the image is mounted read-only.
2. **Runtime environment for the guest**: `TMPDIR` on the SD-backed `cache/`
   mount (the launcher stages large downloads through `tempfile`, and tmpfs
   lives in the kernel library's small memory); `/etc/resolv.conf` written
   from the console's DNS settings; wall-clock time from the console's clock
   (TLS certificate validation needs it); `getrandom` backed by the host's
   random source; `HOME` and `XDG_*` on `data/`.
3. **Count native code**: list every shared object Python loads for the
   launcher's imports and compare with the JIT-mapping budget (constraint C2,
   Phase 1 number). Prefer builds where standard-library extensions are
   compiled into the interpreter.
4. **Guest test scripts** in `tests/guest/python/`, each printing a single
   PASS or FAIL line:
   - imports of every module the launcher imports;
   - `ssl` handshake and a GET of one public, unauthenticated TTR API endpoint
     documented in `api-doc` (one request per test run), plus the same against
     the fake server from Phase 2;
   - Fernet round trip; Argon2id key derivation with the parameters in the
     pinned `encrypt.py`, with time and peak memory recorded;
   - SHA-1 and bz2 decompression of a 100 MB fixture from `cache/`, with
     throughput recorded; a bsdiff patch applied in place;
   - eight concurrent downloads from the fake server with `thread_map`;
   - `tempfile` lands on `cache/`; JSON settings round trip on `data/`;
   - `subprocess.run` and `os.system` fail with a clear exception rather
     than hanging or killing the process (constraint C7).
5. **Keyring backend** `guest/adapter/nx2_keyring.py`: a
   `keyring.backend.KeyringBackend` that stores entries in a file on `data/`
   encrypted with a key derived (Argon2id) from a user secret supplied
   through a callback. No plaintext or obfuscation-only storage. Unit tests
   on macOS; guest test on gx.
6. **Start-up cost**: measure interpreter start to "imports done" on the
   bench and on the console; reduce with lazy imports in our code if needed.

## Deliverables

Reproducible `rootfs.ext4` build with lock file and package manifest, guest
test suite, keyring backend, measurements in `docs/perf/python.md`,
`docs/hardware/phase-04-checklist.md`.

## Acceptance criteria

- [ ] Two consecutive `make rootfs` runs produce images with the same
      SHA-256; image size is reported and under 300 MB (or a stated budget).
- [ ] Every wheel in the image appears in the lock file with a hash; no
      package was installed from source without a note.
- [ ] `make bench` and `make test-nx2like` run all guest Python tests: all
      PASS; show the summary.
- [ ] The HTTPS test validates the server certificate (a test with a wrong
      clock or an untrusted CA fails as it should).
- [ ] Argon2id derivation completes within the kernel library's and guest's
      memory budgets, with the peak recorded.
- [ ] Keyring backend tests pass; the stored file contains none of the test
      passwords in plain or base64 form (asserted by the test).
- [ ] Shared objects loaded for the launcher's imports: count reported and
      below the budget with at least 50% headroom.
- [ ] Hardware (pending human until logged): all guest tests PASS on the
      console; interpreter start to "imports done" under 8 seconds; G4 marked
      in `docs/STATUS.md`.

## Hardware

Deploy the NRO and the new `rootfs.ext4`; the console must be on Wi-Fi with
the Mac's fake server reachable. Run the Python test list, pull logs.

## If blocked

- An extension module fails to load on gx: reduce to the failing relocation
  or syscall with a C reproducer and fix it in the runtime, not by removing
  the module.
- `cryptography`'s wheel needs a newer glibc than the base: raise the base
  distribution version and record it, rather than building OpenSSL yourself.
- DNS or TLS fails only on the console: capture the NAT's view in the log,
  compare with the bench.
