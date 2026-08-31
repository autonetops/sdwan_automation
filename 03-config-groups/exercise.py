"""Module 3 — Config Groups and the asynchronous model (50 min)

Here you write to the fabric for the first time. Three disciplines arrive
together:

  1. **Preview before deploy.** Always. It's free and it's the only honest
     answer to "what exactly is going to change?".
  2. **Wait for the task.** The Manager returns an id and walks away. A script
     that doesn't wait lies about its own result.
  3. **Namespace.** The lab is shared. Everything you create carries your
     `ws<NN>-` prefix. Without it you step on each other.

Run:    export WS_STUDENT=07        # the number the instructor gave you
        python exercise.py --list
        python exercise.py --preview
        python exercise.py --deploy

Check:  python -m pytest ../tests/test_tasks.py -q
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdwan_toolkit import SDWANClient  # noqa: E402
from sdwan_toolkit.configgroup import (  # noqa: E402
    get_associated_devices,
    list_config_groups,
    preview_device_config,
)
from sdwan_toolkit.tasks import wait_for_task  # noqa: E402


def my_prefix() -> str:
    student = os.getenv("WS_STUDENT")
    if not student:
        raise SystemExit(
            "Set WS_STUDENT to the number the instructor gave you. e.g. export WS_STUDENT=07"
        )
    return f"ws{student}-"


# ─────────────────────────────────────────────────────────────────────
# TASK 1 — Find your config group
# ─────────────────────────────────────────────────────────────────────

def my_config_group(client: SDWANClient):
    """Return the ConfigGroup whose name starts with your prefix."""
    # TODO 1.1: list the config groups and return the first whose `name`
    #           starts with my_prefix(). If none matches, raise SystemExit
    #           with a useful message.
    return None


# ─────────────────────────────────────────────────────────────────────
# TASK 2 — Preview: look before you leap
#
# `preview_device_config` returns the CLI that *would* be pushed, without
# pushing it. It is the Manager's own `terraform plan`, and almost nobody
# uses it.
# ─────────────────────────────────────────────────────────────────────

def show_preview(client: SDWANClient, group_id: str, device_uuid: str) -> None:
    # TODO 2.1: call preview_device_config and print the result.
    #           Read the output: can you point at the line that will change?
    pass


# ─────────────────────────────────────────────────────────────────────
# TASK 3 — Deploy, and wait
#
# The POST returns {"parentTaskId": "..."}. The change happens AFTERWARDS.
# Without polling you don't know whether it worked — only that it was accepted.
# ─────────────────────────────────────────────────────────────────────

def run_deploy(client: SDWANClient, group_id: str, device_uuids: list[str]):
    """Trigger the deployment and wait for it. Returns the TaskResult."""
    # TODO 3.1: POST to /v1/config-group/{group_id}/device/deploy
    #           with {"devices": [{"id": uuid}, ...]}
    response = None

    # TODO 3.2: pull out the task id (key "parentTaskId", with "id" as backup).
    #           If neither is there, raise RuntimeError — failing loudly beats
    #           returning silent success.
    task_id = None

    # TODO 3.3: call wait_for_task(). Pick a realistic timeout: a multi-site
    #           deployment easily passes 5 minutes.
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Config groups via the API")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--deploy", action="store_true")
    args = parser.parse_args()

    with SDWANClient.from_vault() as client:
        if args.list:
            for group in list_config_groups(client):
                mark = "→" if group.name.startswith(my_prefix()) else " "
                print(f"{mark} {group.name:<40} {group.id}")
            return

        group = my_config_group(client)
        if group is None:
            return
        print(f"Config group: {group.name} ({group.id})")

        associated = [d.get("id") for d in get_associated_devices(client, group.id)]
        if not associated:
            print("No devices associated with this group. Talk to the instructor.")
            return

        if args.preview:
            show_preview(client, group.id, associated[0])
        elif args.deploy:
            result = run_deploy(client, group.id, associated)
            if result:
                print(result.summary())


if __name__ == "__main__":
    main()
