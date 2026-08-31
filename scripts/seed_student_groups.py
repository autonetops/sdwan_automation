"""INSTRUCTOR ONLY — seed per-student config groups for module 3.

Module 3 expects each student to find a config group named `ws<NN>-…` that
already has a device associated. A device can belong to only ONE config
group, so seeding a student means MOVING one edge out of its site group and
into the student's group. This script does that move — and reverts it.

The student group references the SAME feature profiles as the site group
(profiles are standalone objects; groups only point at them), so the deployed
configuration is identical. Device variable values are carried across.

⚠️ VERIFIED LIMITATION (itrentalBootcamp, 20.15): when the site profiles
carry device-conditional variables for SEVERAL devices (this lab's shared
CLI add-on defines cedge1-* AND cedge2-* variables), a single-device student
group demands values for ALL of them — including the sibling's, which the
moved device never had. The script detects that and refuses BEFORE deploying
anything, leaving the device associated but undeployable; finish the variable
form in the GUI (Configuration → Config Groups → Deploy) or revert. Two
further Manager behaviours this script is shaped around:

  - Detaching a device DELETES its stored variable values in the old group.
    (Recovery, if you get stuck: the values are all readable from
    GET /template/config/running/{uuid} — the device's running config.)
  - The variables GET answers `family`; the PUT demands `solution`
    (set_device_variables handles the rename).

Run with the admin credentials from Vault (the same `secret/sdwan/manager`):

    export VAULT_ADDR=... VAULT_TOKEN=...        # instructor token
    python scripts/seed_student_groups.py --list
    python scripts/seed_student_groups.py --seed 01 --site CG_SITE101 --device cedge1-101
    python scripts/seed_student_groups.py --revert 01

With 5 lab edges there are at most 5 concurrent student groups. Pairs share.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdwan_toolkit import SDWANClient  # noqa: E402
from sdwan_toolkit.configgroup import (  # noqa: E402
    associate_devices,
    deploy,
    find_config_group,
    get_associated_devices,
    get_device_variables,
    list_config_groups,
    set_device_variables,
)
from sdwan_toolkit.inventory import get_devices  # noqa: E402


def student_group_name(student: str, site_group: str) -> str:
    return f"ws{student}-{site_group.lower()}"


def device_by_hostname(client: SDWANClient, hostname: str):
    for d in get_devices(client):
        if d.hostname == hostname:
            return d
    raise SystemExit(f"No device with hostname {hostname!r} in the inventory.")


def variables_for(client: SDWANClient, group_id: str, device_uuid: str) -> list[dict]:
    payload = get_device_variables(client, group_id)
    for dev in payload.get("devices", []):
        if dev.get("device-id") == device_uuid:
            return dev.get("variables", [])
    return []


def move_device(client: SDWANClient, uuid: str, from_gid: str, to_gid: str) -> None:
    """Detach from one group, associate with the other, carry the variables.

    Order matters, learned the hard way:
    - Detaching a device DELETES its stored variable values in the old group,
      so we capture them first — and refuse to start if any is unset, because
      after the detach there is nothing left to recover them from (short of
      reading the device's running config back).
    - The new group's variable entry only exists after the associate, so we
      GET it, fill our captured values into it, and PUT the whole payload
      back (set_device_variables handles the family→solution rename).
    """
    captured = {v["name"]: v["value"] for v in variables_for(client, from_gid, uuid)
                if "value" in v}
    missing = [v["name"] for v in variables_for(client, from_gid, uuid)
               if "value" not in v]
    if not captured or missing:
        raise SystemExit(f"Refusing to move: source group has unset variables "
                         f"{missing or '(none at all)'} for this device. Fix them "
                         f"first — after the detach they are unrecoverable.")

    client.request("DELETE", f"/v1/config-group/{from_gid}/device/associate",
                   json={"devices": [{"id": uuid}]})
    associate_devices(client, to_gid, [uuid])

    payload = get_device_variables(client, to_gid)
    for dev in payload.get("devices", []):
        if dev.get("device-id") != uuid:
            continue
        for var in dev.get("variables", []):
            if "value" not in var and var.get("name") in captured:
                var["value"] = captured[var["name"]]
        gaps = [v["name"] for v in dev.get("variables", []) if "value" not in v]
        if gaps:
            raise SystemExit(f"Variables {gaps} have no value to carry — the device "
                             f"is associated but NOT deployable. Fill them in the GUI "
                             f"(Configuration → Config Groups → Deploy) before deploying.")
    set_device_variables(client, to_gid, payload)
    print(f"  moved {uuid}: {len(captured)} variable values carried")


def cmd_list(client: SDWANClient) -> None:
    for g in list_config_groups(client):
        devs = get_associated_devices(client, g.id)
        print(f"{g.name:<28} {g.id}  devices: {[d.get('id') for d in devs]}")


def cmd_seed(client: SDWANClient, student: str, site_group: str, hostname: str,
             do_deploy: bool) -> None:
    site = find_config_group(client, site_group)
    if site is None:
        raise SystemExit(f"Site group {site_group!r} not found.")
    dev = device_by_hostname(client, hostname)
    if not dev.is_reachable:
        raise SystemExit(f"{hostname} is not reachable — seed a healthy device.")
    associated = {d.get("id") for d in get_associated_devices(client, site.id)}
    if dev.uuid not in associated:
        raise SystemExit(f"{hostname} is not associated with {site_group}.")

    name = student_group_name(student, site_group)
    group = find_config_group(client, name)
    if group is None:
        detail = client.get(f"/v1/config-group/{site.id}")
        profiles = [{"id": p["id"]} for p in detail.get("profiles", [])]
        created = client.post("/v1/config-group", {
            "name": name,
            "description": f"Bootcamp student ws{student} — mirrors {site_group}",
            "solution": "sdwan",
            "profiles": profiles,
        })
        gid = created.get("id") if isinstance(created, dict) else None
        if not gid:
            raise SystemExit(f"Group creation returned no id: {created!r}")
        print(f"created {name} ({gid}) with {len(profiles)} shared profiles")
        group = find_config_group(client, name)
    else:
        print(f"{name} already exists ({group.id})")

    move_device(client, dev.uuid, site.id, group.id)
    if do_deploy:
        result = deploy(client, group.id, [dev.uuid], timeout=900)
        print(f"  deploy: {result.summary()}")
    print(f"done — {hostname} now belongs to {name}")


def cmd_revert(client: SDWANClient, student: str, site_group: str, hostname: str,
               do_deploy: bool) -> None:
    name = student_group_name(student, site_group)
    group = find_config_group(client, name)
    site = find_config_group(client, site_group)
    if group is None or site is None:
        raise SystemExit(f"Need both {name!r} and {site_group!r} to exist.")
    dev = device_by_hostname(client, hostname)

    move_device(client, dev.uuid, group.id, site.id)
    if do_deploy:
        result = deploy(client, site.id, [dev.uuid], timeout=900)
        print(f"  deploy: {result.summary()}")
    client.request("DELETE", f"/v1/config-group/{group.id}")
    print(f"done — {hostname} back in {site_group}, {name} deleted")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed/revert per-student config groups")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--seed", metavar="NN")
    parser.add_argument("--revert", metavar="NN")
    parser.add_argument("--site", help="site config group, e.g. CG_SITE101")
    parser.add_argument("--device", help="edge hostname, e.g. cedge1-101")
    parser.add_argument("--no-deploy", action="store_true",
                        help="move the association but skip the deploy")
    args = parser.parse_args()

    with SDWANClient.from_vault() as client:
        if args.list:
            cmd_list(client)
        elif args.seed:
            if not (args.site and args.device):
                raise SystemExit("--seed needs --site and --device")
            cmd_seed(client, args.seed, args.site, args.device, not args.no_deploy)
        elif args.revert:
            if not (args.site and args.device):
                raise SystemExit("--revert needs --site and --device")
            cmd_revert(client, args.revert, args.site, args.device, not args.no_deploy)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
