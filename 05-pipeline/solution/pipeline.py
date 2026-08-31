"""Module 5 — annotated solution for the validated change pipeline."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sdwan_toolkit import SDWANClient, compare, take_snapshot  # noqa: E402
from sdwan_toolkit.state import FabricSnapshot  # noqa: E402

SNAPSHOTS = Path("snapshots")
# The solution applies the solution's terraform dir. The exercise dir ships
# the module 4 deliberate error (TODO 2.1), which is the student's to fix —
# their own pipeline.py applies ../04-terraform once they have.
TERRAFORM_DIR = Path(__file__).resolve().parents[2] / "04-terraform" / "solution"

# BFD and OMP take time to reconverge after a push. Checking too early reports
# a regression that isn't real — and a pipeline that cries wolf is a pipeline
# people switch off.
CONVERGENCE_WAIT = 60


def precheck(client: SDWANClient) -> FabricSnapshot:
    print("── PRECHECK ──")
    snapshot = take_snapshot(client)

    down = [d for d in snapshot.devices.values() if not d.reachable]
    if down:
        # We don't abort: in a shared lab someone always has a device
        # deliberately down. But we record it, because `compare` only looks at
        # the DIFFERENCE — a device that was already down before and after
        # produces no finding at all, and without this line nobody would notice.
        names = ", ".join(d.hostname for d in down)
        print(f"  ⚠ Already unreachable BEFORE the change: {names}")

    path = snapshot.save(SNAPSHOTS / "before.json")
    print(f"  Snapshot saved to {path} ({len(snapshot.devices)} devices)")
    return snapshot


def apply_change() -> bool:
    print("── APPLY ──")
    # A list of arguments, never shell=True with a built-up string.
    result = subprocess.run(
        ["terraform", "apply", "-auto-approve", "-input=false"],
        cwd=TERRAFORM_DIR,
        text=True,
    )
    return result.returncode == 0


def postcheck(client: SDWANClient, before: FabricSnapshot) -> bool:
    print("── POSTCHECK ──")
    print(f"  Waiting {CONVERGENCE_WAIT}s for convergence…")
    time.sleep(CONVERGENCE_WAIT)

    after = take_snapshot(client)
    after.save(SNAPSHOTS / "after.json")

    difference = compare(before, after)
    print(difference.report())
    return difference.ok


def rollback() -> None:
    print("── ROLLBACK ──")
    # Choice: `terraform apply` with the default variable value, rather than
    # `destroy`. Destroying the whole config group is more violent than the
    # change we are undoing — and a rollback that causes more impact than the
    # original problem is not a rollback, it's a second incident.
    result = subprocess.run(
        ["terraform", "apply", "-auto-approve", "-input=false",
         "-var", "banner_motd=ROLLBACK - previous state restored"],
        cwd=TERRAFORM_DIR,
        text=True,
    )
    if result.returncode == 0:
        print("  Rollback applied.")
    else:
        # A failed rollback is the worst place to be: escalate, don't retry.
        print("  ✗ ROLLBACK FAILED — manual intervention required.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validated change pipeline")
    parser.add_argument("--dry-run", action="store_true")
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
