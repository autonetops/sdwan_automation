"""Module 2 — annotated solution.

The reference implementation lives in `sdwan_toolkit/state.py`; this file is
the same logic written step by step, with the reasoning on show.
"""

import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sdwan_toolkit import SDWANClient, compare, get_devices  # noqa: E402
from sdwan_toolkit.state import (  # noqa: E402
    DeviceState,
    FabricSnapshot,
    get_bfd_sessions,
    get_control_connections,
    get_omp_peers,
)


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Operational snapshot of the fabric")
    parser.add_argument("--save", metavar="FILE")
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
            f"{state.hostname:<20} {state.control_connections_up:>8} "
            f"{state.bfd_sessions_up:>6} {state.omp_peers_up:>6}"
        )

    if args.save:
        print(f"\nSnapshot written to {snapshot.save(args.save)}")

    edges = [e for e in snapshot.devices.values() if e.bfd_sessions_up]
    if edges:
        winner = max(edges, key=lambda e: e.bfd_sessions_up)
        print(f"\n>>> ANSWER: {winner.hostname} with {winner.bfd_sessions_up} BFD sessions up")


if __name__ == "__main__":
    main()
