"""Module 6 — the data model, the schema and the semantic rules.

These run with no lab, no Vault and no network. That is not a convenience:
the `validate` stage of the pipeline is the job that must keep working when
the fabric is down, and a gate that needs the thing it is gating is not a
gate. If this suite needs a Manager, the design is wrong.
"""

import json

import pytest
import yaml

from sdwan_toolkit.datamodel import (
    DataModelError,
    FabricData,
    load_data_model,
    render_tfvars,
    semantic_checks,
    write_tfvars,
)

REPO_MODEL = "06-pipeline/data/fabric.yaml"


def model_dict(**overrides):
    """A valid document, with room to break one thing at a time."""
    payload = {
        "sdwan": {
            "student": "07",
            "system": {"banner": {"motd": "Managed by the pipeline", "login": "Authorized only"}},
            "config_group": {"name": "config-group", "description": "For the bootcamp"},
            "targets": {"edges": ["Site1-Edge1"]},
        }
    }
    payload["sdwan"].update(overrides)
    return payload


@pytest.fixture
def model_file(tmp_path):
    def write(payload):
        path = tmp_path / "fabric.yaml"
        path.write_text(yaml.safe_dump(payload))
        return path
    return write


# ── schema ──────────────────────────────────────────────────────────

def test_a_valid_document_loads(model_file):
    data = load_data_model(model_file(model_dict()))
    assert data.sdwan.student == "07"
    assert data.prefix == "ws07-"


def test_an_unknown_key_is_an_error_not_a_shrug(model_file):
    """The reason every model sets extra="forbid".

    Pydantic's default is to ignore keys it does not recognise, which turns
    `bannner:` into a change that passes every check and does nothing. A typo
    must fail loudly, or the pipeline is lying to you.
    """
    payload = model_dict()
    payload["sdwan"]["system"]["bannner"] = {"motd": "oops"}

    with pytest.raises(DataModelError) as exc:
        load_data_model(model_file(payload))
    assert any("bannner" in problem for problem in exc.value.problems)


def test_the_student_number_must_be_two_digits(model_file):
    with pytest.raises(DataModelError) as exc:
        load_data_model(model_file(model_dict(student="7")))
    assert any("student" in problem for problem in exc.value.problems)


def test_a_missing_required_section_names_its_path(model_file):
    payload = model_dict()
    del payload["sdwan"]["system"]

    with pytest.raises(DataModelError) as exc:
        load_data_model(model_file(payload))
    # The only part of a validation error that saves anyone time is the path.
    assert any(problem.startswith("sdwan.system") for problem in exc.value.problems)


def test_an_empty_motd_is_rejected_by_the_schema(model_file):
    payload = model_dict()
    payload["sdwan"]["system"]["banner"]["motd"] = ""

    with pytest.raises(DataModelError):
        load_data_model(model_file(payload))


def test_broken_yaml_says_so_rather_than_blaming_the_schema(tmp_path):
    path = tmp_path / "fabric.yaml"
    path.write_text("sdwan:\n  student: '07'\n   bad_indent: true\n")

    with pytest.raises(DataModelError, match="not valid YAML"):
        load_data_model(path)


def test_a_missing_file_is_a_data_model_error_not_an_oserror(tmp_path):
    with pytest.raises(DataModelError, match="Cannot read"):
        load_data_model(tmp_path / "nope.yaml")


# ── semantic rules ──────────────────────────────────────────────────
# Shape is one thing, meaning is another. Everything below is a valid
# document that says something unwise.

def test_a_clean_model_has_nothing_to_say():
    assert semantic_checks(FabricData.model_validate(model_dict())) == []


@pytest.mark.parametrize("placeholder", ["TODO", "CHANGEME", "FIXME", "XXX"])
def test_placeholders_never_reach_a_banner(placeholder):
    payload = model_dict()
    payload["sdwan"]["system"]["banner"]["login"] = f"{placeholder} - fill this in"

    problems = semantic_checks(FabricData.model_validate(payload))
    assert any(placeholder in p for p in problems)


def test_placeholders_are_caught_regardless_of_case():
    payload = model_dict()
    payload["sdwan"]["system"]["banner"]["motd"] = "todo: write a real banner"

    assert semantic_checks(FabricData.model_validate(payload))


def test_the_banner_delimiter_would_truncate_the_banner():
    payload = model_dict()
    payload["sdwan"]["system"]["banner"]["motd"] = "Site A ^C Site B"

    problems = semantic_checks(FabricData.model_validate(payload))
    assert any("delimiter" in p for p in problems)


def test_a_name_that_already_carries_the_prefix_is_caught():
    """The rule a schema cannot express.

    ws07-ws07-config-group is a perfectly good string. Knowing that the
    renderer already adds the prefix is knowledge about the pipeline, not
    about the shape of the document — which is why it lives in a semantic
    rule and not in the schema.
    """
    payload = model_dict(config_group={"name": "ws07-config-group", "description": "x"})

    problems = semantic_checks(FabricData.model_validate(payload))
    assert any("prefix" in p for p in problems)


def test_a_change_that_targets_nothing_cannot_be_verified():
    payload = model_dict(targets={"edges": []})

    problems = semantic_checks(FabricData.model_validate(payload))
    assert any("targets.edges" in p for p in problems)


def test_a_duplicated_target_is_reported_once():
    payload = model_dict(targets={"edges": ["Site1-Edge1", "Site1-Edge1", "Site2-Edge1"]})

    problems = [p for p in semantic_checks(FabricData.model_validate(payload))
                if "more than once" in p]
    assert len(problems) == 1
    assert "Site1-Edge1" in problems[0]
    assert "Site2-Edge1" not in problems[0]


# ── rendering ───────────────────────────────────────────────────────

def test_rendering_produces_exactly_the_variables_module_5_declares():
    variables = render_tfvars(FabricData.model_validate(model_dict()))

    assert variables == {
        "student": "07",
        "banner_motd": "Managed by the pipeline",
        "banner_login": "Authorized only",
        "config_group_name": "config-group",
        "config_group_description": "For the bootcamp",
    }


def test_targets_are_not_rendered_to_terraform():
    """The data model is bigger than any one consumer of it.

    Terraform has no use for `targets`; precheck() does. A data model that
    only contains what the current tool reads is a config file with extra
    steps.
    """
    assert "targets" not in render_tfvars(FabricData.model_validate(model_dict()))


def test_the_rendered_file_is_byte_identical_for_identical_input(tmp_path):
    """A generated file whose key order wanders is a diff nobody reads."""
    data = FabricData.model_validate(model_dict())

    first = write_tfvars(data, tmp_path / "a" / "generated.auto.tfvars.json").read_bytes()
    second = write_tfvars(data, tmp_path / "b" / "generated.auto.tfvars.json").read_bytes()

    assert first == second
    assert json.loads(first)["student"] == "07"


# ── the file this repository actually ships ─────────────────────────

def test_the_shipped_data_model_matches_the_schema():
    """Pins the file the exercise starts from.

    Deliberately says nothing about the semantic rules: the shipped model
    fails one on purpose, and fixing it is the first thing a student does.
    A test that broke when they did the exercise would be a trap.
    """
    data = load_data_model(REPO_MODEL)
    assert data.sdwan.targets.edges, "the shipped model must target something"
    assert render_tfvars(data).keys() == {
        "student", "banner_motd", "banner_login",
        "config_group_name", "config_group_description",
    }


# ── the seam between module 6 and module 5 ──────────────────────────

TERRAFORM_DIRS = ["05-terraform", "05-terraform/solution"]


def declared_variables(variables_tf):
    import re
    return set(re.findall(r'^variable\s+"([^"]+)"', variables_tf, re.MULTILINE))


@pytest.mark.parametrize("terraform_dir", TERRAFORM_DIRS)
def test_every_rendered_variable_is_declared_in_terraform(terraform_dir):
    """The one failure mode Terraform will NOT report as an error.

    A key in a *.auto.tfvars.json file that no `variable` block declares gets
    a *warning*:

        Warning: Value for undeclared variable
        The root module does not declare a variable named "banner_motdd" but
        a value was found in file "generated.auto.tfvars.json".

    A warning. The plan carries on, the apply succeeds, and the change you
    thought you made simply did not happen. Rename a field in
    `render_tfvars()` without touching variables.tf and that is what you get
    — which is why this assertion exists here rather than being left to CI.
    """
    from pathlib import Path

    declared = declared_variables(Path(terraform_dir, "variables.tf").read_text())
    rendered = set(render_tfvars(FabricData.model_validate(model_dict())))

    undeclared = rendered - declared
    assert not undeclared, (
        f"{terraform_dir}/variables.tf does not declare {sorted(undeclared)}. "
        "Terraform would only warn, and the change would silently not happen."
    )
