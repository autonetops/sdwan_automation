#!/usr/bin/env python3
"""Stage 1 of the pipeline — validate.

The cheapest job in the pipeline and the one that saves the most time. It
needs no Vault, no Manager, no network: it reads `data/fabric.yaml` and
answers one question — *is this change even coherent?*

    python validate.py                    # validate data/fabric.yaml
    python validate.py path/to/other.yaml

Exit code 0 = the change may proceed to `plan`. 1 = it may not.

Two kinds of check, and they are not the same thing:

    schema     Is it the right SHAPE?    `motd` is a string; `bannner` is
                                         not a key I know about.
    semantic   Does it MEAN something sane?
                                         A string containing "CHANGEME" is a
                                         perfectly good string, and must not
                                         reach a router.

A schema catches the change you typed wrong. Semantic rules catch the change
you meant.
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdwan_toolkit.datamodel import (  # noqa: E402
    DataModelError,
    FabricData,
    load_data_model,
    semantic_checks,
)

DEFAULT_MODEL = Path(__file__).parent / "data" / "fabric.yaml"


# ─────────────────────────────────────────────────────────────────────
# TASK 1 — a rule of your own
# ─────────────────────────────────────────────────────────────────────

def local_checks(data: FabricData) -> list[str]:
    """Rules this repository cares about, on top of the toolkit's.

    `sdwan_toolkit.datamodel.semantic_checks()` ships the rules that are true
    for everybody. This function is where *your* team's rules go — the ones
    that come out of your last outage, your naming standard, your change
    policy. A validator you cannot extend is a validator you route around.

    Return a list of human-readable problems. Empty list = nothing to say.
    """
    problems: list[str] = []

    # TODO 1.1: add one rule. Suggestions, in rough order of usefulness:
    #
    #   • `config_group.description` must not be empty — six months from now
    #     it is the only clue to why the group exists.
    #   • the MOTD must name the team that owns the box, so whoever reads it
    #     at 3am knows who to call.
    #   • `config_group.name` must match a naming standard, e.g. all
    #     lowercase and hyphenated: re.fullmatch(r"[a-z0-9-]+", name).
    #
    # Write the message the way you would want to read it at the top of a
    # failed pipeline: say what is wrong AND what to do about it.

    return problems


# ─────────────────────────────────────────────────────────────────────
# The report
# ─────────────────────────────────────────────────────────────────────

def _summary(data: FabricData) -> str:
    """One line describing what the model asks for. Read by the reviewer."""
    sdwan = data.sdwan
    return (
        f"{data.prefix}{sdwan.config_group.name} · "
        f"banner motd {len(sdwan.system.banner.motd)} chars · "
        f"{len(sdwan.targets.edges)} target edge(s)"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the SD-WAN data model")
    parser.add_argument("model", nargs="?", default=DEFAULT_MODEL, type=Path,
                        help=f"data model to validate (default: {DEFAULT_MODEL})")
    args = parser.parse_args()

    print(f"── VALIDATE {args.model} ──")

    # ── schema ──────────────────────────────────────────────────────
    try:
        data = load_data_model(args.model)
    except DataModelError as exc:
        print(f"  ✗ schema      {exc}")
        for problem in exc.problems:
            print(f"                {problem}")
        # We stop here on purpose. Semantic rules run against a parsed model,
        # and there is no model to run them against — reporting "motd is
        # missing" AND "motd contains a placeholder" would be noise.
        return 1
    print(f"  ✓ schema      {_summary(data)}")

    # ── semantics ───────────────────────────────────────────────────
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
