"""Module 5 — Validated change pipeline (30 min)

This is the capstone. It brings everything together:

    snapshot BEFORE  →  apply the change  →  snapshot AFTER  →  compare
                                                                  ↓
                                                regressed?  →  ROLLBACK

The idea the whole bootcamp has been building toward: **a change without
automatic verification is not automation, it is faster typing.**

Run:    python pipeline.py --dry-run     # snapshots only, changes nothing
        python pipeline.py               # the full cycle

Exit code 0 if the fabric came out the same or better, 1 if it regressed.
That exit code is what GitLab CI uses to fail the pipeline.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdwan_toolkit import SDWANClient, compare, take_snapshot  # noqa: E402
from sdwan_toolkit.state import FabricSnapshot  # noqa: E402

SNAPSHOTS = Path("snapshots")


# ─────────────────────────────────────────────────────────────────────
# TASK 1 — The reference snapshot
# ─────────────────────────────────────────────────────────────────────

def precheck(client: SDWANClient) -> FabricSnapshot:
    """Snapshot BEFORE the change. Also the entry gate.

    If the fabric is already broken before you touch it, the change should not
    start — otherwise you inherit a problem that wasn't yours and lose the
    ability to tell your regression apart from the one already there.
    """
    print("── PRECHECK ──")
    snapshot = take_snapshot(client)

    # TODO 1.1: if any device has `reachable=False`, report it on screen.
    #           Decide (and justify in the README) whether that should abort
    #           the pipeline. Hint: in a shared lab, always aborting is
    #           unworkable; aborting when a TARGET EDGE is down is not.

    # TODO 1.2: save the snapshot to SNAPSHOTS / "before.json" and return it.
    return snapshot


# ─────────────────────────────────────────────────────────────────────
# TASK 2 — Apply the change
# ─────────────────────────────────────────────────────────────────────

def apply_change() -> bool:
    """Apply the change with Terraform. Returns True if apply succeeded."""
    # TODO 2.1: run `terraform apply -auto-approve` inside ../04-terraform
    #           using subprocess.run. Return True when returncode == 0.
    #
    #           ⚠️ Don't use shell=True with an interpolated string. Pass a
    #              list of arguments — that's the difference between a command
    #              and an injection.
    return False


# ─────────────────────────────────────────────────────────────────────
# TASK 3 — Verify and decide
# ─────────────────────────────────────────────────────────────────────

def postcheck(client: SDWANClient, before: FabricSnapshot) -> bool:
    """Snapshot AFTER + verdict. True = safe to keep the change."""
    print("── POSTCHECK ──")

    # TODO 3.1: take the after snapshot and save it to SNAPSHOTS / "after.json".

    # TODO 3.2: compare(before, after), print the .report() and return .ok
    #
    #           ⏱️ THINK ABOUT TIME: BFD and OMP do not reconverge instantly.
    #              An immediate postcheck reports a regression that isn't real.
    #              How long should you wait? Justify your choice.
    return False


# ─────────────────────────────────────────────────────────────────────
# TASK 4 — Undo
# ─────────────────────────────────────────────────────────────────────

def rollback() -> None:
    """Undo the change. The part almost every homegrown pipeline forgets."""
    print("── ROLLBACK ──")
    # TODO 4.1: Terraform keeps the previous state. The simplest way to revert
    #           in the lab is `terraform apply` with the old variable value, or
    #           `terraform destroy -target=...`.
    #           Implement it and explain in the README why you chose that path.
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Validated change pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="take both snapshots without applying any change")
    args = parser.parse_args()

    SNAPSHOTS.mkdir(exist_ok=True)

    with SDWANClient.from_vault() as client:
        before = precheck(client)

        if args.dry_run:
            print("\n[dry-run] No change applied.")
            return 0 if postcheck(client, before) else 1

        if not apply_change():
            print("Apply failed. Nothing to verify.")
            return 1

        if postcheck(client, before):
            print("\n✓ Fabric intact. Change kept.")
            return 0

        print("\n✗ Regression detected.")
        rollback()
        return 1


if __name__ == "__main__":
    sys.exit(main())
