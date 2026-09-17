"""Stages 3 and 4 — annotated solution for the validated change pipeline."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sdwan_toolkit import SDWANClient, compare, take_snapshot  # noqa: E402
from sdwan_toolkit.datamodel import (  # noqa: E402
    DataModelError,
    FabricData,
    load_data_model,
    render_tfvars,
    semantic_checks,
    write_tfvars,
)
from sdwan_toolkit.state import FabricSnapshot  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
SNAPSHOTS = Path("snapshots")

# One data model, shared with the exercise. A second copy would be a second
# truth, and the entire premise of this module is that there is one.
DATA_MODEL = REPO_ROOT / "06-pipeline" / "data" / "fabric.yaml"
DATA_MODEL_IN_GIT = "06-pipeline/data/fabric.yaml"

# The solution applies the solution's terraform dir. 05-terraform/ ships the
# module 5 planted errors (TODO 2.1, TODO 4.1), which are the student's to
# fix — their own pipeline.py points at their own directory once they have.
# TF_DIR lets the pipeline override this without editing code — it is set in
# .gitlab-ci.yml, repo-relative. A hardcoded path here that disagrees with the
# pipeline is a mismatch nobody notices until an apply lands somewhere
# unexpected.
_tf_dir = os.getenv("TF_DIR")
TERRAFORM_DIR = REPO_ROOT / (_tf_dir or "05-terraform/solution")
TFVARS = TERRAFORM_DIR / "generated.auto.tfvars.json"

# BFD and OMP take time to reconverge after a push. Checking too early reports
# a regression that isn't real — and a pipeline that cries wolf is a pipeline
# people switch off. 60s is the lab's number, arrived at by watching: it is
# comfortably past when BFD comes back and comfortably short of a coffee.
CONVERGENCE_WAIT = 60


class PrecheckFailed(RuntimeError):
    """The fabric was not in a state to receive the change."""


def _terraform(*args: str) -> int:
    """Run terraform in TERRAFORM_DIR. A list of arguments, never shell=True.

    No -var flags anywhere: the rendered *.auto.tfvars.json is loaded
    automatically, which is what keeps this job and the plan job from ever
    disagreeing about what was supposed to happen.
    """
    return subprocess.run(["terraform", *args], cwd=TERRAFORM_DIR, text=True).returncode


# ── TASK 1, solved ──────────────────────────────────────────────────

def precheck(client: SDWANClient, data: FabricData) -> FabricSnapshot:
    print("── PRECHECK ──")
    snapshot = take_snapshot(client)

    down = [d for d in snapshot.devices.values() if not d.reachable]
    if down:
        # We report every one of them, because `compare` only looks at the
        # DIFFERENCE: a device that was down before and after produces no
        # finding at all, and without this line nobody would ever notice.
        names = ", ".join(sorted(d.hostname for d in down))
        print(f"  ⚠ Already unreachable BEFORE the change: {names}")

    # But we only ABORT for a device this change targets. That distinction is
    # what makes the gate usable in a shared lab: somebody always has a device
    # deliberately down, and a gate that fires on other people's work is a
    # gate that gets commented out in week two.
    targets = {name.lower() for name in data.sdwan.targets.edges}
    blocked = sorted(d.hostname for d in down if d.hostname.lower() in targets)
    if blocked:
        raise PrecheckFailed(
            f"target edge(s) unreachable: {', '.join(blocked)}. "
            "Changing a device you cannot verify afterwards is not a change, "
            "it is a hope."
        )

    # A target that the fabric has never heard of is the other half of the
    # same check — and a far more common mistake than a device being down.
    known = {d.hostname.lower() for d in snapshot.devices.values()}
    unknown = sorted(name for name in data.sdwan.targets.edges if name.lower() not in known)
    if unknown:
        raise PrecheckFailed(
            f"target edge(s) not in the fabric: {', '.join(unknown)}. "
            "Check sdwan.targets.edges against the hostnames the Manager reports."
        )

    path = snapshot.save(SNAPSHOTS / "before.json")
    print(f"  Snapshot saved to {path} ({len(snapshot.devices)} devices)")
    print(f"  Targets verified reachable: {', '.join(data.sdwan.targets.edges)}")
    return snapshot


# ── TASK 2, solved ──────────────────────────────────────────────────

def apply_change(data: FabricData) -> bool:
    print("── APPLY ──")

    # Render here and not only in the plan stage, because the plan stage was a
    # different container. The alternative is to ship the saved plan between
    # jobs as an artifact — which this repo deliberately does not do, because
    # Terraform persists every data source it read into the plan file, and one
    # of those is the Manager password out of Vault.
    out = write_tfvars(data, TFVARS)
    print(f"  Rendered {DATA_MODEL.name} → {out.name}")

    return _terraform("apply", "-auto-approve", "-input=false") == 0


# ── TASK 3, solved ──────────────────────────────────────────────────

def postcheck(client: SDWANClient, before: FabricSnapshot, wait: int) -> bool:
    print("── POSTCHECK ──")
    print(f"  Waiting {wait}s for convergence…")
    time.sleep(wait)

    after = take_snapshot(client)
    after.save(SNAPSHOTS / "after.json")

    difference = compare(before, after)
    print(difference.report())
    return difference.ok


# ── TASK 4, solved ──────────────────────────────────────────────────

def previous_data_model() -> FabricData | None:
    """The data model as of the previous commit — the rollback target.

    The thing to notice: there is no backup here, and nobody had to remember
    to take one. The previous state of the fabric is the previous commit, and
    it has been sitting in Git the whole time. That is most of the argument
    for putting the change in a file in the first place.
    """
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"HEAD~1:{DATA_MODEL_IN_GIT}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # No previous version: a first commit, or a shallow clone with
        # depth 1 (GitLab's default — see GIT_DEPTH in .gitlab-ci.yml).
        print(f"  ⚠ No previous version in git: {result.stderr.strip()}")
        return None

    try:
        return FabricData.model_validate(yaml.safe_load(result.stdout))
    except Exception as exc:  # noqa: BLE001 - any parse failure is the same answer
        print(f"  ⚠ The previous data model does not parse: {exc}")
        return None


def rollback(data: FabricData) -> None:
    print("── ROLLBACK ──")

    previous = previous_data_model()
    if previous is None:
        print("  ✗ Nothing to roll back to. MANUAL INTERVENTION REQUIRED.")
        return

    # The case that looks like success and isn't. If the previous data model
    # renders to the same variables, this file did not cause the regression —
    # so re-applying it is a no-op, and reporting "rolled back" would be a
    # lie. Something else moved: somebody in the GUI, another student's
    # change, or the fabric itself.
    if render_tfvars(previous) == render_tfvars(data):
        print("  ✗ The previous data model is identical to this one.")
        print("    The regression did not come from this file, so there is")
        print("    nothing here to undo. ESCALATE — do not retry.")
        return

    # Chosen over `terraform destroy`: destroying the whole config group is
    # more violent than the change we are undoing, and a rollback that causes
    # more impact than the original problem is not a rollback, it is a second
    # incident. Re-applying the previous data model moves exactly the values
    # that moved, and nothing else.
    write_tfvars(previous, TFVARS)
    print(f"  Re-applying the previous data model "
          f"(banner motd: {previous.sdwan.system.banner.motd!r})")

    if _terraform("apply", "-auto-approve", "-input=false") == 0:
        print("  ✓ Rollback applied.")
    else:
        # A failed rollback is the worst place a pipeline can be: the fabric
        # is now in neither the old state nor the new one. Escalate, don't
        # retry — a retry loop here is how a bad change becomes an outage.
        print("  ✗ ROLLBACK FAILED — MANUAL INTERVENTION REQUIRED.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validated change pipeline")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default=DATA_MODEL, type=Path)
    parser.add_argument("--wait", type=int, default=CONVERGENCE_WAIT)
    args = parser.parse_args()

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
