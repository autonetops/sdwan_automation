"""The data model — the change as data, not as HCL.

Module 6's deliverable, and the thing that makes a pipeline reviewable.

Until now the change lived in `terraform.tfvars`: HCL, read by one tool,
diffed by nobody. A merge request that says

    -banner_motd = "Managed by Terraform - AutoNetOps Bootcamp"
    +banner_motd = "Managed by the pipeline"

is a diff only a Terraform user can review. So we lift the change one level
up, into a YAML document that describes **what the fabric should be** — and
then generate Terraform's inputs from it.

    data/fabric.yaml  ──render──▶  *.auto.tfvars.json  ──▶  terraform

Three things follow from that split, and they are the whole lesson:

1. **The change gets a schema.** A typo in a key name fails in five seconds in
   the `validate` stage, not forty minutes later in `apply`.
2. **The change gets rules.** A schema says "motd is a string". A *semantic*
   rule says "a string containing the word TODO must not reach a router".
   Those are different checks and they fail at different times — which is why
   `semantic_checks()` is a separate function below.
3. **The data model outlives the tool.** `targets.edges` is never rendered to
   Terraform; the Python pipeline reads it. A data model describes the change,
   not one tool's inputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

# Text that means "somebody meant to come back to this". A banner is read by
# every person who logs into the box, every day, for as long as nobody
# notices — which is how "CHANGEME" ends up in a customer screenshot.
PLACEHOLDERS = ("TODO", "CHANGEME", "FIXME", "XXX")

# The cap this data model imposes. The exact number matters far less than the
# fact that a bound exists somewhere it can fail cheaply — in `validate`,
# offline, rather than as a 400 from the Manager halfway through a deploy.
MAX_BANNER_CHARS = 2048


class DataModelError(ValueError):
    """The file is unreadable, or does not match the schema.

    Carries the individual problems so a caller can print them one per line —
    a validator that says "invalid" and stops is a validator people work
    around instead of with.
    """

    def __init__(self, message: str, problems: list[str] | None = None) -> None:
        super().__init__(message)
        self.problems = problems or []


# ── the schema ──────────────────────────────────────────────────────
# `extra="forbid"` everywhere, and that is deliberate. The default — silently
# ignoring keys it does not know — turns a typo into a change that passes
# every check and does nothing. `bannner:` should be an error, not a no-op.


class Banner(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motd: str = Field(min_length=1, max_length=MAX_BANNER_CHARS)
    login: str = Field(min_length=1, max_length=MAX_BANNER_CHARS)


class System(BaseModel):
    model_config = ConfigDict(extra="forbid")

    banner: Banner


class ConfigGroupSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    description: str = ""


class Targets(BaseModel):
    """Which devices this change is aimed at.

    Terraform never sees this. `precheck()` in pipeline.py does: it is the
    difference between "a device somewhere in the shared lab is down" and
    "the device we are about to change is down".
    """

    model_config = ConfigDict(extra="forbid")

    edges: list[str] = Field(default_factory=list)


class Sdwan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student: str = Field(pattern=r"^[0-9]{2}$")
    system: System
    config_group: ConfigGroupSpec
    targets: Targets = Field(default_factory=Targets)


class FabricData(BaseModel):
    """The whole document. One top-level key, so the file can grow."""

    model_config = ConfigDict(extra="forbid")

    sdwan: Sdwan

    @property
    def prefix(self) -> str:
        """Everything this student creates carries it. One shared lab."""
        return f"ws{self.sdwan.student}-"


# ── semantic rules ──────────────────────────────────────────────────
# Everything above is *shape*. Everything here is *meaning*, and the split is
# the point: a schema cannot know that the renderer already adds the ws07-
# prefix, so a schema cannot catch ws07-ws07-config-group.
#
# Every rule below is offline and deterministic. The validate stage must keep
# working when the lab is down — a gate that needs the thing it is gating is
# not a gate.


def semantic_checks(data: FabricData) -> list[str]:
    """Return a list of problems. Empty list means the model is sane."""
    problems: list[str] = []
    sdwan = data.sdwan
    banner = sdwan.system.banner

    for field_name, text in (("motd", banner.motd), ("login", banner.login)):
        where = f"sdwan.system.banner.{field_name}"

        found = [p for p in PLACEHOLDERS if p in text.upper()]
        if found:
            problems.append(
                f"{where}: contains the placeholder {found[0]!r}. "
                "A banner is read by everyone who logs in, every day."
            )

        # IOS-XE terminates a banner with a delimiter character, and the
        # rendered CLI uses ^C. Text carrying the delimiter truncates the
        # banner at that point — the config applies, and it is wrong.
        if "^C" in text or "\x03" in text:
            problems.append(
                f"{where}: contains the banner delimiter '^C'. "
                "The banner would be truncated there."
            )

    # The renderer prefixes names with ws<NN>-. A name that carries the prefix
    # already becomes ws07-ws07-config-group: valid, deployable, and wrong.
    if sdwan.config_group.name.lower().startswith("ws"):
        problems.append(
            f"sdwan.config_group.name: {sdwan.config_group.name!r} looks like it "
            f"already carries a student prefix. The renderer adds {data.prefix!r} "
            "for you — write the bare name."
        )

    if not sdwan.targets.edges:
        problems.append(
            "sdwan.targets.edges: empty. A change that targets no device cannot "
            "be verified, and an unverifiable change is the one you should not "
            "be pushing through a pipeline."
        )

    duplicates = sorted({e for e in sdwan.targets.edges if sdwan.targets.edges.count(e) > 1})
    if duplicates:
        problems.append(
            f"sdwan.targets.edges: listed more than once: {', '.join(duplicates)}."
        )

    return problems


# ── loading ─────────────────────────────────────────────────────────


def _format_errors(exc: ValidationError) -> list[str]:
    """pydantic's errors, one readable line each.

    `loc` is a tuple of path segments; joining it with dots gives the student
    the exact key to open, which is the only part of a validation error that
    saves anybody time.
    """
    lines = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"]) or "<document>"
        lines.append(f"{location}: {error['msg']}")
    return lines


def load_data_model(path: str | Path) -> FabricData:
    """Read and schema-validate the data model. Raises DataModelError.

    Note what this does NOT do: the semantic rules. Callers run those
    separately, because "the file is the wrong shape" and "the file is the
    right shape but says something unwise" deserve different messages.
    """
    path = Path(path)
    try:
        raw = path.read_text()
    except OSError as exc:
        raise DataModelError(f"Cannot read {path}: {exc}") from exc

    try:
        payload = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        # Not valid YAML at all — usually indentation. Worth its own message,
        # because a schema error here would be misleading.
        raise DataModelError(f"{path} is not valid YAML: {exc}") from exc

    if not isinstance(payload, dict):
        raise DataModelError(f"{path} must contain a mapping, got {type(payload).__name__}.")

    try:
        return FabricData.model_validate(payload)
    except ValidationError as exc:
        problems = _format_errors(exc)
        raise DataModelError(
            f"{path} does not match the schema ({len(problems)} problem(s)).", problems
        ) from exc


# ── rendering ───────────────────────────────────────────────────────


def render_tfvars(data: FabricData) -> dict[str, Any]:
    """The data model, as the variables module 5 declares.

    A deliberately boring function, and that is the design: everything
    interesting — validation, rules, defaults — happened before this point.
    Rendering is a translation, and a translation that makes decisions is a
    translation you will be debugging.

    `targets` is absent on purpose. Terraform has no use for it; the Python
    pipeline does. The data model is bigger than any one consumer of it.
    """
    sdwan = data.sdwan
    return {
        "student": sdwan.student,
        "banner_motd": sdwan.system.banner.motd,
        "banner_login": sdwan.system.banner.login,
        "config_group_name": sdwan.config_group.name,
        "config_group_description": sdwan.config_group.description,
    }


def write_tfvars(data: FabricData, path: str | Path) -> Path:
    """Render the model and write it where Terraform will find it.

    `sort_keys` so the file is byte-identical for identical input. A generated
    file whose key order wanders produces a diff on every run, and a diff that
    is always noisy is a diff nobody reads.

    Lives here rather than in `render.py` because two callers need it —
    `render.py` in the plan stage and `pipeline.py` in the deploy stage — and
    the one thing worse than a generated file is two of them, written by two
    pieces of code that drifted apart.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(render_tfvars(data), indent=2, sort_keys=True) + "\n")
    return path
