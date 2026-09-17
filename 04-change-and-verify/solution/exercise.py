"""Module 4 — annotated solution.

The reference implementations live in `sdwan_toolkit/state.py`,
`sdwan_toolkit/tasks.py` and `sdwan_toolkit/configgroup.py`; this file is the
same logic written step by step, with the reasoning on show.
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

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

# How long to let the fabric settle after a deploy reports success.
# 45s is a compromise: long enough for BFD/OMP to reconverge in this lab,
# short enough that nobody switches the check off out of boredom. Measure it
# in your own fabric — don't inherit this number.
SETTLE_SECONDS = 45


def my_prefix() -> str:
    student = os.getenv("WS_STUDENT")
    if not student:
        raise SystemExit("Set WS_STUDENT. e.g. export WS_STUDENT=07")
    return f"ws{student}-"


# ── PART A — state as data ──────────────────────────────────────────


def count_up(rows: list[dict], *fields: str) -> int:
    total = 0
    for row in rows:
        for field in fields:
            if str(row.get(field, "")).lower() in {"up", "ok"}:
                total += 1
                break  # the break stops us counting the same row twice
    return total


def collect(client: SDWANClient, device) -> DeviceState:
    state = DeviceState(
        system_ip=device.system_ip,
        hostname=device.hostname,
        reachable=device.is_reachable,
    )

    # Early return: a device that is down won't answer, it only costs timeouts.
    if not device.is_reachable:
        return state

    state.control_connections_up = count_up(
        get_control_connections(client, device.system_ip), "state", "status"
    )

    # BFD only exists between edges. Asking a controller is a wasted call.
    if device.is_edge:
        bfd = get_bfd_sessions(client, device.system_ip)
        state.bfd_sessions_up = count_up(bfd, "state", "status")
        # The peer LIST, not just the count: "6 before, 6 after" can still
        # hide a swapped peer, and that is a real regression.
        state.bfd_peers = sorted(
            {
                row.get("system-ip", "")
                for row in bfd
                if str(row.get("state", "")).lower() == "up"
            }
            - {""}
        )

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
            f"{state.hostname:<20} {state.control_connections_up:>8} "
            f"{state.bfd_sessions_up:>6} {state.omp_peers_up:>6}"
        )


# ── PART B — the change ─────────────────────────────────────────────


def my_config_group(client: SDWANClient):
    prefix = my_prefix()
    group = next(
        (g for g in list_config_groups(client) if g.name.startswith(prefix)), None
    )
    if group is None:
        # Name what to check. "Not found" costs the next person twenty minutes.
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


# ── PART C — the verdict ────────────────────────────────────────────


def change_and_verify(client: SDWANClient, group, device_uuids: list[str]) -> bool:
    print("── BEFORE ──")
    before = take_snapshot(client)
    print_snapshot(before)
    before.save("snapshots/before.json")

    print("\n── DEPLOY ──")
    result = run_deploy(client, group.id, device_uuids)
    print(result.summary())

    # The task says "success" when the Manager finished pushing — not when the
    # fabric has reconverged. Snapshotting immediately reports regressions that
    # resolve themselves thirty seconds later, and a check that cries wolf is a
    # check people turn off.
    print(f"\nLetting the fabric settle for {SETTLE_SECONDS}s…")
    time.sleep(SETTLE_SECONDS)

    print("\n── AFTER ──")
    after = take_snapshot(client)
    print_snapshot(after)
    after.save("snapshots/after.json")

    print("\n── VERDICT ──")
    diff = compare(before, after)
    print(diff.report())
    return diff.ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Change the fabric, and prove it")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--snapshot", metavar="FILE")
    parser.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--deploy", action="store_true")
    args = parser.parse_args()

    if args.compare:
        before = FabricSnapshot.load(args.compare[0])
        after = FabricSnapshot.load(args.compare[1])
        diff = compare(before, after)
        print(diff.report())
        # The verdict has to be readable by a machine, not just by you.
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

            edges = [e for e in snapshot.devices.values() if e.bfd_sessions_up]
            if edges:
                winner = max(edges, key=lambda e: e.bfd_sessions_up)
                print(
                    f"\n>>> ANSWER (a): {winner.hostname} "
                    f"with {winner.bfd_sessions_up} BFD sessions up"
                )
            return 0

        group = my_config_group(client)
        print(f"Config group: {group.name} ({group.id})")

        associated = [d.get("id") for d in get_associated_devices(client, group.id)]
        if not associated:
            print("No devices associated. Talk to the instructor.")
            return 1

        if args.preview:
            show_preview(client, group.id, associated[0])
            return 0

        if args.deploy:
            ok = change_and_verify(client, group, associated)
            print(f"\n>>> ANSWER (b): the change {'PASSED' if ok else 'FAILED'}")
            # The exit code is the point: it is what CI reads in module 6.
            return 0 if ok else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
