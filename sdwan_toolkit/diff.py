"""Snapshot comparison — the judge of the change.

A snapshot diff is not a text `diff`. It is **asymmetric on purpose**: gaining
a BFD session is good, losing one is bad. The pipeline needs that opinion to
decide between moving forward and rolling back.

Decision rule: only regressions fail. Improvements and neutral changes appear
in the report but do not block the deployment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .state import DeviceState, FabricSnapshot


class Severity(str, Enum):
    REGRESSION = "regression"    # got worse — fails the change
    IMPROVEMENT = "improvement"  # got better — informational
    INFO = "info"                # changed without getting worse


@dataclass
class Finding:
    system_ip: str
    hostname: str
    metric: str
    before: object
    after: object
    severity: Severity

    def __str__(self) -> str:
        arrow = {
            Severity.REGRESSION: "✗",
            Severity.IMPROVEMENT: "✓",
            Severity.INFO: "·",
        }[self.severity]
        return f"{arrow} {self.hostname} ({self.system_ip}) {self.metric}: {self.before} → {self.after}"


@dataclass
class SnapshotDiff:
    findings: list[Finding] = field(default_factory=list)
    missing_devices: list[str] = field(default_factory=list)
    new_devices: list[str] = field(default_factory=list)

    @property
    def regressions(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.REGRESSION]

    @property
    def ok(self) -> bool:
        """True when it is safe to move forward."""
        return not self.regressions and not self.missing_devices

    def report(self) -> str:
        lines: list[str] = []
        if self.missing_devices:
            lines.append(f"✗ Gone from the fabric: {', '.join(sorted(self.missing_devices))}")
        if self.new_devices:
            lines.append(f"· New in the fabric: {', '.join(sorted(self.new_devices))}")
        lines.extend(str(f) for f in self.findings)
        if not lines:
            return "No differences between the snapshots."
        verdict = "PASS" if self.ok else "FAIL"
        return "\n".join(lines) + f"\n\nVerdict: {verdict}"


# Metrics where "higher is better". A drop is a regression.
_HIGHER_IS_BETTER = (
    ("control_connections_up", "control connections"),
    ("bfd_sessions_up", "BFD sessions"),
    ("omp_peers_up", "OMP peers"),
)


def _compare_device(before: DeviceState, after: DeviceState) -> list[Finding]:
    findings: list[Finding] = []

    if before.reachable and not after.reachable:
        findings.append(
            Finding(after.system_ip, after.hostname, "reachability", "reachable",
                    "unreachable", Severity.REGRESSION)
        )
    elif not before.reachable and after.reachable:
        findings.append(
            Finding(after.system_ip, after.hostname, "reachability", "unreachable",
                    "reachable", Severity.IMPROVEMENT)
        )

    for attr, label in _HIGHER_IS_BETTER:
        old, new = getattr(before, attr), getattr(after, attr)
        if new < old:
            severity = Severity.REGRESSION
        elif new > old:
            severity = Severity.IMPROVEMENT
        else:
            continue
        findings.append(Finding(after.system_ip, after.hostname, label, old, new, severity))

    lost_peers = set(before.bfd_peers) - set(after.bfd_peers)
    if lost_peers:
        findings.append(
            Finding(after.system_ip, after.hostname, "BFD peers lost", sorted(lost_peers),
                    [], Severity.REGRESSION)
        )

    return findings


def compare(before: FabricSnapshot, after: FabricSnapshot) -> SnapshotDiff:
    """Compare two snapshots and return a verdict."""
    diff = SnapshotDiff()
    diff.missing_devices = sorted(before.devices.keys() - after.devices.keys())
    diff.new_devices = sorted(after.devices.keys() - before.devices.keys())

    for system_ip in sorted(before.devices.keys() & after.devices.keys()):
        diff.findings.extend(_compare_device(before.devices[system_ip], after.devices[system_ip]))

    return diff
