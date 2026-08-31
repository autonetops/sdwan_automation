"""The judge of the change. Pure tests — no network, they run anywhere."""

from sdwan_toolkit.diff import Severity, compare
from sdwan_toolkit.state import DeviceState, FabricSnapshot


def _snapshot(**overrides):
    base = dict(
        system_ip="10.255.255.11", hostname="Site1-Edge1", reachable=True,
        control_connections_up=2, bfd_sessions_up=4,
        bfd_peers=["10.255.255.12", "10.255.255.13"], omp_peers_up=2,
    )
    base.update(overrides)
    return FabricSnapshot(taken_at="2026-01-01T00:00:00+00:00",
                          devices={base["system_ip"]: DeviceState(**base)})


def test_identical_snapshots_produce_no_findings():
    diff = compare(_snapshot(), _snapshot())
    assert diff.findings == []
    assert diff.ok


def test_losing_a_bfd_session_is_a_regression():
    diff = compare(_snapshot(), _snapshot(bfd_sessions_up=2))
    assert not diff.ok
    assert diff.regressions[0].metric == "BFD sessions"


def test_gaining_a_bfd_session_does_not_fail():
    diff = compare(_snapshot(), _snapshot(bfd_sessions_up=6))
    assert diff.ok
    assert diff.findings[0].severity is Severity.IMPROVEMENT


def test_device_going_unreachable_is_a_regression():
    diff = compare(_snapshot(), _snapshot(reachable=False))
    assert not diff.ok


def test_losing_a_bfd_peer_is_a_regression():
    diff = compare(_snapshot(), _snapshot(bfd_peers=["10.255.255.12"]))
    assert not diff.ok
    assert any("lost" in f.metric for f in diff.regressions)


def test_a_device_that_disappeared_fails():
    after = FabricSnapshot(taken_at="2026-01-01T01:00:00+00:00", devices={})
    diff = compare(_snapshot(), after)
    assert not diff.ok
    assert diff.missing_devices == ["10.255.255.11"]


def test_snapshot_survives_a_round_trip_to_disk(tmp_path):
    original = _snapshot()
    path = original.save(tmp_path / "before.json")
    reloaded = FabricSnapshot.load(path)
    assert compare(original, reloaded).ok
