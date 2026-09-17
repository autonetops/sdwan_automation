#!/usr/bin/env python3
"""Stage 2, first half — render the data model into Terraform's inputs.

    data/fabric.yaml  ──▶  05-terraform/solution/generated.auto.tfvars.json

Terraform loads every `*.auto.tfvars.json` in its working directory without
being asked, which is why this is the whole integration: no `-var` flags to
keep in sync between the plan job and the apply job, and no chance of the two
disagreeing.

    python render.py                 # to the directory the pipeline deploys
    python render.py --out ../05-terraform/generated.auto.tfvars.json
    python render.py --print         # to stdout, change nothing

The output is generated, gitignored, and must never be edited by hand. If you
find yourself wanting to, the thing you actually want is a new field in
`data/fabric.yaml` and a line in `render_tfvars()`.

── One precedence rule worth knowing ────────────────────────────────
Terraform reads variables in this order, each beating the one before:

    TF_VAR_*  <  terraform.tfvars  <  *.auto.tfvars(.json)  <  -var

So this file beats `TF_VAR_student` from the environment, and it beats a
`terraform.tfvars` left over on somebody's laptop. That is the point — the
data model is the source of truth, and a source of truth that the
environment can quietly override is not one.
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdwan_toolkit.datamodel import (  # noqa: E402
    DataModelError,
    load_data_model,
    render_tfvars,
    semantic_checks,
    write_tfvars,
)

HERE = Path(__file__).resolve().parent
DEFAULT_MODEL = HERE / "data" / "fabric.yaml"

# The directory the pipeline deploys from. 05-terraform/ (without /solution)
# ships module 5's planted errors, so CI would fail against it forever by
# design; once you have fixed them, `--out ../05-terraform/...` renders into
# your own.
DEFAULT_OUT = HERE.parent / "05-terraform" / "solution" / "generated.auto.tfvars.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the data model to tfvars")
    parser.add_argument("--model", default=DEFAULT_MODEL, type=Path)
    parser.add_argument("--out", default=DEFAULT_OUT, type=Path)
    parser.add_argument("--print", dest="to_stdout", action="store_true",
                        help="write to stdout instead of to --out")
    args = parser.parse_args()

    # Fail closed. The pipeline runs `validate` before it runs `render`, so in
    # CI this is belt and braces — but on a laptop nobody ran validate, and a
    # renderer that happily turns a broken model into valid-looking Terraform
    # input is a renderer that launders the error.
    try:
        data = load_data_model(args.model)
    except DataModelError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        for problem in exc.problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    problems = semantic_checks(data)
    if problems:
        print(f"✗ {args.model} is the right shape but fails {len(problems)} rule(s):",
              file=sys.stderr)
        for problem in problems:
            print(f"  • {problem}", file=sys.stderr)
        print("Run validate.py for the full report.", file=sys.stderr)
        return 1

    variables = render_tfvars(data)

    if args.to_stdout:
        print(json.dumps(variables, indent=2, sort_keys=True))
        return 0

    out = write_tfvars(data, args.out)
    print(f"── RENDER ──\n  {args.model}\n  → {out}")
    print(f"  {len(variables)} variables, config group "
          f"{data.prefix}{data.sdwan.config_group.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
