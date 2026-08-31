"""Module 3 — annotated solution."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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
        raise SystemExit("Set WS_STUDENT. e.g. export WS_STUDENT=07")
    return f"ws{student}-"


def my_config_group(client: SDWANClient):
    prefix = my_prefix()
    group = next((g for g in list_config_groups(client) if g.name.startswith(prefix)), None)
    if group is None:
        raise SystemExit(
            f"No config group starting with '{prefix}'. "
            f"Check WS_STUDENT, or run --list to see what exists."
        )
    return group


def show_preview(client: SDWANClient, group_id: str, device_uuid: str) -> None:
    print("\n─── CLI that WOULD be applied (nothing was pushed) ───")
    print(preview_device_config(client, group_id, device_uuid))
    print("──────────────────────────────────────────────────────\n")


def run_deploy(client: SDWANClient, group_id: str, device_uuids: list[str]):
    response = client.post(
        f"/v1/config-group/{group_id}/device/deploy",
        {"devices": [{"id": uuid} for uuid in device_uuids]},
    )

    # The key name changed between releases; we accept both.
    task_id = None
    if isinstance(response, dict):
        task_id = response.get("parentTaskId") or response.get("id")
    if not task_id:
        # Fail loudly. The worst possible outcome would be returning "ok" here.
        raise RuntimeError(f"Deployment returned no task id. Response: {response!r}")

    print(f"Task {task_id} accepted. Follow it in the GUI under Monitor → Tasks.")

    # 15 min: multi-site deployment is slow. A short timeout produces a false
    # negative, and a false negative makes people re-run the deployment —
    # which is worse than waiting.
    return wait_for_task(client, task_id, timeout=900, interval=5)


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
        print(f"Config group: {group.name} ({group.id})")

        associated = [d.get("id") for d in get_associated_devices(client, group.id)]
        if not associated:
            print("No devices associated. Talk to the instructor.")
            return

        if args.preview:
            show_preview(client, group.id, associated[0])
        elif args.deploy:
            print(run_deploy(client, group.id, associated).summary())


if __name__ == "__main__":
    main()
