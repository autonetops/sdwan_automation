#!/usr/bin/env python3
"""Stage 1 — annotated solution for the data model validator."""

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sdwan_toolkit.datamodel import (  # noqa: E402
    DataModelError,
    FabricData,
    load_data_model,
    semantic_checks,
)

# The solution validates the same file the exercise does. There is one data
# model in this repository, and that is the whole idea — a second copy is a
# second truth.
DEFAULT_MODEL = Path(__file__).resolve().parents[1] / "data" / "fabric.yaml"

NAME_STANDARD = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def local_checks(data: FabricData) -> list[str]:
    """TASK 1, solved — two rules that are ours, not the toolkit's."""
    problems: list[str] = []
    sdwan = data.sdwan

    # Rule 1. An empty description is free to write and expensive to lack.
    # The person who needs it is not you today; it is somebody in six months
    # asking why this group exists and whether they can delete it.
    if not sdwan.config_group.description.strip():
        problems.append(
            "sdwan.config_group.description: empty. Say what this group is for "
            "— in six months it is the only clue anyone will have."
        )

    # Rule 2. A naming standard is only a standard if something enforces it.
    # Enforced here, offline, in the validate stage: the cheapest place a
    # naming argument can possibly happen.
    if not NAME_STANDARD.fullmatch(sdwan.config_group.name):
        problems.append(
            f"sdwan.config_group.name: {sdwan.config_group.name!r} does not match "
            "the naming standard (lowercase, digits and single hyphens). "
            "Try 'branch-config-group'."
        )

    return problems


def _summary(data: FabricData) -> str:
    sdwan = data.sdwan
    return (
        f"{data.prefix}{sdwan.config_group.name} · "
        f"banner motd {len(sdwan.system.banner.motd)} chars · "
        f"{len(sdwan.targets.edges)} target edge(s)"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the SD-WAN data model")
    parser.add_argument("model", nargs="?", default=DEFAULT_MODEL, type=Path)
    args = parser.parse_args()

    print(f"── VALIDATE {args.model} ──")

    try:
        data = load_data_model(args.model)
    except DataModelError as exc:
        print(f"  ✗ schema      {exc}")
        for problem in exc.problems:
            print(f"                {problem}")
        return 1
    print(f"  ✓ schema      {_summary(data)}")

    problems = semantic_checks(data) + local_checks(data)
    if problems:
        print(f"  ✗ semantic    {len(problems)} problem(s)")
        for problem in problems:
            print(f"                • {problem}")
        return 1
    print("  ✓ semantic    no problems")

    print("\nThe data model is valid. Safe to plan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
