"""Module 4 — Change the fabric, and prove it (50 min)

The first time you write to the fabric — and the first time you make the
fabric prove you didn't break it.

    snapshot BEFORE  →  preview  →  deploy  →  wait  →  snapshot AFTER  →  compare

Three disciplines arrive at once, and they only make sense together:

  1. **State as data.** "It worked" is an opinion until you have a comparable
     snapshot on both sides of the change.
  2. **Preview before deploy.** Free, safe, and the only honest answer to
     "what exactly is going to change?".
  3. **Wait for the task.** The Manager returns an id and walks away. A script
     that doesn't wait lies about its own result.

Plus one rule: the lab is shared. Everything you touch carries your `ws<NN>-`
prefix.

Run:    export WS_STUDENT=07
        python exercise.py --list                       # find your config group
        python exercise.py --snapshot before.json       # just look
        python exercise.py --preview                    # dry run
        python exercise.py --deploy                     # the full cycle
        python exercise.py --compare before.json after.json

Check:  python -m pytest ../tests/test_diff.py ../tests/test_tasks.py -q
"""

import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdwan_toolkit import SDWANClient, compare, get_devices  # noqa: E402
from sdwan_toolkit.configgroup import (  # noqa: E402
    get_associated_devices,
    list_config_groups,
    preview_device_config,
)
from sdwan_toolkit.state import (  # noqa: E402
    DeviceState,
    FabricSnapshot,
    get_bfd_sessions,
    get_control_connections,
    get_omp_peers,
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
# PART A — STATE AS DATA
# ─────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────
# TASK 1 — Count what is "up"
#
# The Manager API is not consistent: depending on the endpoint the state
# field is called `state`, `status` or `operstate`, and the value can be
# "up", "Up" or "UP". Writing `if row["state"] == "up"` works today and
# breaks on the next endpoint.
#
# Normalizing at the edge — the moment data comes in — is what keeps
# `row.get("state") or row.get("status")` from spreading through everything.
# ─────────────────────────────────────────────────────────────────────


def count_up(rows: list[dict], *fields: str) -> int:
    """Count rows whose state field indicates 'up' (or 'ok')."""
    # TASK 1.1: for each row, check each candidate field in `fields`.
    #           Normalize with str(...).lower() before comparing.
    #           Count each row ONCE, even if two fields match.
    return 0


# ─────────────────────────────────────────────────────────────────────
# TASK 2 — Collect one device's state
#
# ⚠️ COST: these endpoints are real-time. The Manager queries the device
#    across the control plane to answer. They are expensive and the lab is
#    shared with the whole class. Don't collect what you won't compare.
# ─────────────────────────────────────────────────────────────────────


def collect(client: SDWANClient, device) -> DeviceState:
    state = DeviceState(
        system_ip=device.system_ip,
        hostname=device.hostname,
        reachable=device.is_reachable,
    )

    # TASK 2.1: if the device is NOT reachable, return `state` right now.
    #           Querying a device that is down only burns timeouts — and in a
    #           shared lab, your timeouts are everyone's latency.

    # Given: control connections. Note the two candidate field names.
    state.control_connections_up = count_up(
        get_control_connections(client, device.system_ip), "state", "status"
    )

    # TASK 2.2: for edges ONLY (device.is_edge), collect the BFD sessions.
    #           Store the count in state.bfd_sessions_up, and the sorted list
    #           of `system-ip` of the peers that are up in state.bfd_peers.
    #
    #           Two reasons for the peer list, not just the count:
    #           controllers have no BFD (asking wastes a call), and "6 before,
    #           6 after" can still hide a swapped peer. The diff checks both.

    # Given: OMP peers.
    state.omp_peers_up = count_up(
        get_omp_peers(client, device.system_ip), "state", "status"
    )

    return state


def take_snapshot(client: SDWANClient) -> FabricSnapshot:
    snapshot = FabricSnapshot(taken_at=datetime.now(timezone.utc).isoformat())
    for device in get_devices(client):
        if device.system_ip:
            snapshot.devices[device.system_ip] = collect(client, device)
    return snapshot


def print_snapshot(snapshot: FabricSnapshot) -> None:
    print(f"\n{'HOSTNAME':<20} {'CONTROL':>8} {'BFD':>6} {'OMP':>6}")
    print("-" * 44)
    for state in snapshot.devices.values():
        print(
            f"{state.hostname:<20} "
            f"{state.control_connections_up:>8} "
            f"{state.bfd_sessions_up:>6} "
            f"{state.omp_peers_up:>6}"
        )


# ─────────────────────────────────────────────────────────────────────
# PART B — THE CHANGE
# ─────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────
# TASK 3 — Find your group, and look before you leap
#
# Coming from templates, the mental map is:
#     feature template → parcel      device template → config group
#     attach           → associate + deploy
#
# `preview_device_config` returns the CLI that *would* be pushed, without
# pushing it. It is the Manager's own `terraform plan`, and almost nobody
# uses it.
# ─────────────────────────────────────────────────────────────────────


def my_config_group(client: SDWANClient):
    """Return the ConfigGroup whose name starts with your prefix."""
    # TASK 3.1: list the config groups and return the first whose `name`
    #           starts with my_prefix(). If none matches, raise SystemExit
    #           with a message that says what to check — not "not found".
    return None


def show_preview(client: SDWANClient, group_id: str, device_uuid: str) -> None:
    # TASK 3.2: call preview_device_config and print the result.
    #           Then actually read it: can you point at the line that will
    #           change? If you can't, you are not ready to deploy.
    pass


# ─────────────────────────────────────────────────────────────────────
# TASK 4 — Deploy, and wait
#
# The POST returns {"parentTaskId": "..."}. The change happens AFTERWARDS.
#
#     POST /v1/config-group/{id}/device/deploy  →  {"parentTaskId": "abc-123"}
#                                                            │
#     GET /device/action/status/abc-123  ← polling ──────────┘
#
# Without polling you don't know whether it worked — only that it was
# accepted. Those are very different claims.
# ─────────────────────────────────────────────────────────────────────


def run_deploy(client: SDWANClient, group_id: str, device_uuids: list[str]):
    """Trigger the deployment and wait for it. Returns the TaskResult."""
    # TASK 4.1: POST to /v1/config-group/{group_id}/device/deploy
    #           with {"devices": [{"id": uuid}, ...]}
    response = None

    # TASK 4.2: pull out the task id (key "parentTaskId", with "id" as a
    #           backup — the name changed between releases). If neither is
    #           there, raise RuntimeError. Returning a silent success here
    #           would be the single worst thing this script could do.
    task_id = None

    # TASK 4.3: call wait_for_task(). Pick a realistic timeout: a multi-site
    #           deployment easily passes 5 minutes, and a false timeout makes
    #           people re-run the deploy — which is worse than waiting.
    #
    #           While it runs, open the GUI: Monitor → Tasks. That is the same
    #           task your code is polling.
    return None


# ─────────────────────────────────────────────────────────────────────
# PART C — THE VERDICT
# ─────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────
# TASK 5 — Tie it together
#
# This is the module. Everything above is a part; this is the whole:
# a change that checks its own work and reports a verdict a machine can act on.
#
# `compare()` is deliberately ASYMMETRIC. Gaining a BFD session is good;
# losing one is bad. A text diff doesn't know that — yours does. That opinion
# is what lets module 6's pipeline decide between carrying on and rolling back.
# ─────────────────────────────────────────────────────────────────────


def change_and_verify(client: SDWANClient, group, device_uuids: list[str]) -> bool:
    """before → deploy → after → verdict. True means safe to keep."""
    print("── BEFORE ──")
    before = take_snapshot(client)
    print_snapshot(before)
    before.save("snapshots/before.json")

    print("\n── DEPLOY ──")
    result = run_deploy(client, group.id, device_uuids)
    if result is None:
        print("Deployment returned nothing. Is TASK 4 still open?")
        return False
    print(result.summary())

    # TASK 5.1: ⏱️ WAIT before snapshotting again. BFD and OMP do not
    #           reconverge the instant a task reports "success". Snapshot too
    #           early and you report a regression that isn't real — and a
    #           pipeline that cries wolf is a pipeline people switch off.
    #           How long? Pick a number and be able to defend it.

    print("\n── AFTER ──")
    after = take_snapshot(client)
    print_snapshot(after)
    after.save("snapshots/after.json")

    # TASK 5.2: compare(before, after), print the .report(), and return .ok
    #
    #           Then read the report and ask the uncomfortable question:
    #           compare() only looks at the DIFFERENCE. A device that was
    #           already down before and is still down after produces no
    #           finding at all. Is that correct, or a defect?
    #           (The answer lives in module 6's precheck().)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Change the fabric, and prove it")
    parser.add_argument("--list", action="store_true", help="list config groups")
    parser.add_argument(
        "--snapshot", metavar="FILE", help="snapshot only, then write it out"
    )
    parser.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    parser.add_argument(
        "--preview", action="store_true", help="dry run, changes nothing"
    )
    parser.add_argument(
        "--deploy", action="store_true", help="the full before/after cycle"
    )
    args = parser.parse_args()

    # Offline: comparing two files needs no Manager at all. Note the exit
    # code — the verdict has to be readable by a machine, not just by you.
    if args.compare:
        before = FabricSnapshot.load(args.compare[0])
        after = FabricSnapshot.load(args.compare[1])
        diff = compare(before, after)
        print(diff.report())
        return 0 if diff.ok else 1

    with SDWANClient.from_vault() as client:
        if args.list:
            for group in list_config_groups(client):
                mark = "→" if group.name.startswith(my_prefix()) else " "
                print(f"{mark} {group.name:<40} {group.id}")
            return 0

        if args.snapshot:
            snapshot = take_snapshot(client)
            print_snapshot(snapshot)
            print(f"\nSnapshot written to {snapshot.save(args.snapshot)}")

            # TASK 2.3: which edge has the MOST BFD sessions up?
            #           That is half of your module 4 answer.
            return 0

        group = my_config_group(client)
        if group is None:
            print("No config group. Is TASK 3 still open?")
            return 1
        print(f"Config group: {group.name} ({group.id})")

        associated = [d.get("id") for d in get_associated_devices(client, group.id)]
        if not associated:
            print("No devices associated with this group. Talk to the instructor.")
            return 1

        if args.preview:
            show_preview(client, group.id, associated[0])
            return 0

        if args.deploy:
            return 0 if change_and_verify(client, group, associated) else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
