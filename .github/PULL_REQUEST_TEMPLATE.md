## Summary

<!-- What this PR does and why. Phase and sub-task. -->

Phase: phase-NN

## Acceptance checklist

<!-- Copy the phase's acceptance criteria. Beside each item put the evidence:
     the command and its quoted output, a CI run link, or a log in
     docs/hardware/. A criterion that needs the console is "pending human"
     until its log exists. Never write "works on hardware" from inference. -->

- [ ] criterion — evidence

## Pending hardware

<!-- Items that need the console, with the checklist path. "None" if none. -->

## Gates

<!-- Gates G1–G8 this PR moves, with the evidence. "None" if none. -->

## Checks

- [ ] `make lint` and `make test` pass locally
- [ ] No game files, no secrets, launcher submodule unchanged (CI guard rails)
- [ ] `docs/STATUS.md` updated
- [ ] Upstream APIs used are noted in `docs/upstream-notes.md` with commit hashes
- [ ] New design decisions have an ADR in `docs/adr/`
- [ ] `THIRD_PARTY.md` updated if a dependency was added
