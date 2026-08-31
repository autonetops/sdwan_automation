# Module 5 — Validated change pipeline (30 min)

The capstone. Everything you built, together.

```
snapshot BEFORE  →  apply the change  →  snapshot AFTER  →  compare
                                                              │
                                              regressed?  →  ROLLBACK
```

## The thesis of the bootcamp

> A change without automatic verification is not automation. It's faster typing.

A script that pushes config faster than you only made you wrong faster. What
changes the game is the fabric being able to **fail its own change**.

## Get to work

```bash
cd 05-pipeline
python pipeline.py --dry-run    # snapshots only, changes nothing
python pipeline.py              # the full cycle
```

Exit code `0` = fabric intact. `1` = regressed (and already rolled back). That
exit code is what CI uses to fail the pipeline.

## The three decisions the exercise asks for

The TODOs don't have one right answer. They have a **justification**:

1. **Should precheck abort if a device is already down?**
   In a shared lab, always aborting is unworkable. But `compare()` only looks
   at the difference — you at least need to *record* it.

2. **How long to wait before the postcheck?**
   BFD and OMP don't reconverge instantly. Checking too early reports a
   regression that isn't real. And a pipeline that cries wolf is a pipeline
   people switch off.

3. **Rollback via `apply` with the old value, or `destroy`?**
   Destroying the whole config group is more violent than the change you're
   undoing. **A rollback that causes more impact than the original problem
   isn't a rollback — it's a second incident.**

## The pipelines

`.gitlab-ci.yml` (and `.github/workflows/change-validation.yml`) run this for
real. Note the shape:

- **Merge request** → offline tests + `terraform plan`. Safe, runs on any MR.
- **Default branch** → apply with verification and rollback, **manual**, behind
  an environment.
- **Secrets** → the only secret in CI is the Vault token. Everything else comes
  from Vault at runtime, and the snapshots are kept as artifacts for evidence.

Good automation is not the kind that applies fastest. It's the kind that errs
toward the safe side.

## Where to go next

- Swap the homegrown rollback for the Manager's native **config-rollback timer**.
- Manager alarms over webhook → event-driven automation.
- `terraform plan` posted automatically as an MR comment.
- Extend `compare()` with app-route SLA, not just session counts.
