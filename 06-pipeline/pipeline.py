"""Stages 3 and 4 of the pipeline — deploy, with a verdict.

`validate` said the change is coherent. `plan` said what it will do. This is
the job that does it — and the only one that can still say no afterwards.

    precheck  →  render  →  apply  →  wait  →  postcheck  →  compare
        │                                                       │
    target edge down?                                      regressed?
        └─ ABORT                                                └─ ROLLBACK

The idea the whole bootcamp has been building toward:

    A change without automatic verification is not automation.
    It is faster typing.

Run:
    python pipeline.py --dry-run          # both snapshots, changes nothing
    python pipeline.py                    # the full cycle
    python pipeline.py --wait 10          # shorter convergence wait, for a demo

Exit code 0 if the fabric came out the same or better, 1 if it regressed —
having already rolled back. That exit code is what the deploy job reports.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdwan_toolkit import SDWANClient, compare, take_snapshot  # noqa: E402
from sdwan_toolkit.datamodel import (  # noqa: E402
    DataModelError,
    FabricData,
    load_data_model,
    semantic_checks,
)
from sdwan_toolkit.state import FabricSnapshot  # noqa: E402

HERE = Path(__file__).resolve().parent
SNAPSHOTS = Path("snapshots")
DATA_MODEL = HERE / "data" / "fabric.yaml"

# Where the change is applied from. 05-terraform/ is yours — the one with the
# module 5 planted errors in it. Once you have fixed them this is the right
# directory; until then, point it at 05-terraform/solution.
# TF_DIR lets the pipeline override this without editing code — it is set in
# .gitlab-ci.yml, repo-relative. A hardcoded path here that disagrees with the
# pipeline is a mismatch nobody notices until an apply lands somewhere
# unexpected.
_tf_dir = os.getenv("TF_DIR")
TERRAFORM_DIR = HERE.parent / (_tf_dir or "05-terraform")
TFVARS = TERRAFORM_DIR / "generated.auto.tfvars.json"

CONVERGENCE_WAIT = 60


class PrecheckFailed(RuntimeError):
    """The fabric was not in a state to receive the change."""


# ─────────────────────────────────────────────────────────────────────
# TASK 1 — The reference snapshot, and the gate
# ─────────────────────────────────────────────────────────────────────

def precheck(client: SDWANClient, data: FabricData) -> FabricSnapshot:
    """Snapshot BEFORE the change. Also the entry gate.

    If the fabric is already broken before you touch it, the change should not
    start — otherwise you inherit a problem that wasn't yours and lose the
    ability to tell your regression apart from the one already there.
    """
    print("── PRECHECK ──")
    snapshot = take_snapshot(client)

    # TODO 1.1: report every device with `reachable=False` on screen, then
    #           decide what to do about it.
    #
    #           The decision — and this is the one worth arguing about in the
    #           room: in a shared lab, aborting because SOME device is down is
    #           unworkable; somebody always has one deliberately down. Aborting
    #           because a device THIS CHANGE TARGETS is down is not.
    #
    #           `data.sdwan.targets.edges` is a list of hostnames. That key
    #           exists for exactly this: it is what turns "a device is down"
    #           into "the device we are about to reconfigure is down".
    #
    #           Raise PrecheckFailed to abort. Note WHY in the README.

    # TODO 1.2: save the snapshot to SNAPSHOTS / "before.json" and return it.
    #           FabricSnapshot.save() takes the path and returns it back.
    return snapshot


# ─────────────────────────────────────────────────────────────────────
# TASK 2 — Apply the change
# ─────────────────────────────────────────────────────────────────────

def apply_change(data: FabricData) -> bool:
    """Render the data model, then let Terraform apply it. True on success."""
    print("── APPLY ──")

    # TODO 2.1: write the data model out as Terraform's inputs, to TFVARS.
    #           `write_tfvars(data, TFVARS)` from sdwan_toolkit.datamodel does
    #           it in one line. Import it at the top.
    #
    #           Why here, when the plan stage already rendered it? Because the
    #           plan stage was a different container. The alternative is to
    #           pass the saved plan between jobs as an artifact — read the
    #           comment in .gitlab-ci.yml about why this repo does not.

    # TODO 2.2: run `terraform apply -auto-approve -input=false` in
    #           TERRAFORM_DIR with subprocess.run. Return True on returncode 0.
    #
    #           ⚠️ Don't use shell=True with an interpolated string. Pass a
    #              list of arguments — that's the difference between a command
    #              and an injection.
    #
    #           Note what you do NOT pass: any -var flags. The rendered
    #           *.auto.tfvars.json is loaded automatically, which is what keeps
    #           the plan job and this job from ever disagreeing.
    return False


# ─────────────────────────────────────────────────────────────────────
# TASK 3 — Verify and decide
# ─────────────────────────────────────────────────────────────────────

def postcheck(client: SDWANClient, before: FabricSnapshot, wait: int) -> bool:
    """Snapshot AFTER + verdict. True = safe to keep the change."""
    print("── POSTCHECK ──")

    # TODO 3.1: wait `wait` seconds, then take the after snapshot and save it
    #           to SNAPSHOTS / "after.json".
    #
    #           ⏱️ THINK ABOUT TIME: BFD and OMP do not reconverge instantly.
    #              An immediate postcheck reports a regression that isn't real,
    #              and a pipeline that cries wolf is a pipeline people switch
    #              off. How long is long enough? Justify your number.

    # TODO 3.2: compare(before, after), print the .report(), return .ok
    return False


# ─────────────────────────────────────────────────────────────────────
# TASK 4 — Undo
# ─────────────────────────────────────────────────────────────────────

def previous_data_model() -> FabricData | None:
    """The data model as of the previous commit — the rollback target.

    This is the part that only works because the change lives in Git. The
    previous version of the fabric is not a backup somebody remembered to
    take: it is the commit before this one, and it has been there all along.
    """
    # TODO 4.1: read the previous committed version of data/fabric.yaml with
    #           `git show HEAD~1:06-pipeline/data/fabric.yaml` (subprocess,
    #           capture_output=True, text=True), parse it with
    #           FabricData.model_validate(yaml.safe_load(...)), and return it.
    #
    #           Return None if git has no previous version — a first commit, a
    #           shallow clone. The caller must handle that: a rollback that
    #           crashes is worse than one that refuses.
    return None


def rollback(data: FabricData) -> None:
    """Undo the change. The part almost every homegrown pipeline forgets."""
    print("── ROLLBACK ──")

    # TODO 4.2: get the previous data model, render it over TFVARS, and run
    #           terraform apply again.
    #
    #           The choice to justify in the README: this, or
    #           `terraform destroy`? Destroying the whole config group is more
    #           violent than the change you are undoing. **A rollback that
    #           causes more impact than the original problem isn't a rollback,
    #           it's a second incident.**
    #
    #           And the case worth handling explicitly: if the previous data
    #           model renders to exactly the same variables, the regression did
    #           not come from this file — so there is nothing here to undo.
    #           Say so, loudly, and escalate. Silence is the wrong answer.
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Validated change pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="take both snapshots without applying any change")
    parser.add_argument("--model", default=DATA_MODEL, type=Path,
                        help=f"data model to deploy (default: {DATA_MODEL})")
    parser.add_argument("--wait", type=int, default=CONVERGENCE_WAIT,
                        help="seconds to wait for convergence before the postcheck")
    args = parser.parse_args()

    # Fail closed, again. The validate stage already ran these checks — but
    # this script is also run by hand, on a laptop, where it didn't.
    try:
        data = load_data_model(args.model)
    except DataModelError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        for problem in exc.problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    problems = semantic_checks(data)
    if problems:
        print(f"✗ {args.model} fails {len(problems)} rule(s). Run validate.py.",
              file=sys.stderr)
        return 1

    SNAPSHOTS.mkdir(exist_ok=True)

    with SDWANClient.from_vault() as client:
        try:
            before = precheck(client, data)
        except PrecheckFailed as exc:
            print(f"\n✗ Precheck refused the change: {exc}")
            return 1

        if args.dry_run:
            print("\n[dry-run] No change applied.")
            return 0 if postcheck(client, before, args.wait) else 1

        if not apply_change(data):
            print("Apply failed. Nothing to verify.")
            return 1

        if postcheck(client, before, args.wait):
            print("\n✓ Fabric intact. Change kept.")
            return 0

        print("\n✗ Regression detected.")
        rollback(data)
        return 1


if __name__ == "__main__":
    sys.exit(main())
