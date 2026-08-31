"""Module 2 — Operational state as data (50 min)

Goal: produce a snapshot of the fabric that can be saved, versioned and
compared. Without it, "the change worked" is an opinion.

Run:    python exercise.py --save before.json
        python exercise.py --save after.json
        python exercise.py --compare before.json after.json

Check:  python -m pytest ../tests/test_diff.py -q
"""

import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdwan_toolkit import SDWANClient, compare, get_devices  # noqa: E402
from sdwan_toolkit.state import (  # noqa: E402
    DeviceState,
    FabricSnapshot,
    get_bfd_sessions,
    get_control_connections,
    get_omp_peers,
)


# ─────────────────────────────────────────────────────────────────────
# TASK 1 — Count what is "up"
#
# The Manager API is not consistent: depending on the endpoint the state
# field is called `state`, `status` or `operstate`, and the value can be
# "up", "Up" or "UP". Writing `if row["state"] == "up"` works today and
# breaks on the next endpoint.
# ─────────────────────────────────────────────────────────────────────

def count_up(rows: list[dict], *fields: str) -> int:
    """Count rows whose state field indicates 'up' (or 'ok')."""
    # TODO 1.1: for each row, check each candidate field in `fields`.
    #           Normalize with str(...).lower() before comparing.
    #           Count each row ONCE, even if two fields match.
    return 0


# ─────────────────────────────────────────────────────────────────────
# TASK 2 — Collect one device's state
#
# ⚠️ COST: these endpoints are real-time. The Manager will query the device
#    across the control plane. They are expensive and the lab is shared with
#    the whole class. Don't collect what you won't compare, and never query a
#    device you already know is unreachable.
# ─────────────────────────────────────────────────────────────────────

def collect(client: SDWANClient, device) -> DeviceState:
    state = DeviceState(
        system_ip=device.system_ip,
        hostname=device.hostname,
        reachable=device.is_reachable,
    )

    # TODO 2.1: if the device is NOT reachable, return `state` right now.
    #           Querying a device that is down only burns timeouts.

    # TODO 2.2: control connections → get_control_connections(client, system_ip)
    #           Count the ones that are up into state.control_connections_up.

    # TODO 2.3: for edges ONLY (device.is_edge), collect the BFD sessions.
    #           Store the count in state.bfd_sessions_up and the list of
    #           system-ip of the peers that are up in state.bfd_peers.
    #           Controllers have no BFD — asking returns an empty list and
    #           wastes a call.

    # TODO 2.4: OMP peers → get_omp_peers(client, system_ip)

    return state


def take_snapshot(client: SDWANClient) -> FabricSnapshot:
    snapshot = FabricSnapshot(taken_at=datetime.now(timezone.utc).isoformat())
    for device in get_devices(client):
        if device.system_ip:
            snapshot.devices[device.system_ip] = collect(client, device)
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Operational snapshot of the fabric")
    parser.add_argument("--save", metavar="FILE", help="take a snapshot and write it out")
    parser.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    args = parser.parse_args()

    if args.compare:
        before = FabricSnapshot.load(args.compare[0])
        after = FabricSnapshot.load(args.compare[1])
        print(compare(before, after).report())
        return

    with SDWANClient.from_vault() as client:
        snapshot = take_snapshot(client)

    print(f"{'HOSTNAME':<20} {'CONTROL':>8} {'BFD':>6} {'OMP':>6}")
    print("-" * 44)
    for state in snapshot.devices.values():
        print(
            f"{state.hostname:<20} "
            f"{state.control_connections_up:>8} "
            f"{state.bfd_sessions_up:>6} "
            f"{state.omp_peers_up:>6}"
        )

    if args.save:
        path = snapshot.save(args.save)
        print(f"\nSnapshot written to {path}")

    # TODO 3.1: run against the lab and note — which edge has the MOST BFD
    #           sessions up? That is your module 2 answer.


if __name__ == "__main__":
    main()
