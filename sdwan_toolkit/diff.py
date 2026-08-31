"""Comparação de retratos — o juiz da mudança.

Um diff de snapshot não é um `diff` de texto. Ele é **assimétrico de
propósito**: ganhar sessão BFD é bom, perder é ruim. O pipeline precisa dessa
opinião para decidir entre seguir em frente e fazer rollback.

Regra de decisão: só regressão reprova. Melhorias e mudanças neutras entram no
relatório, mas não derrubam o deploy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .state import DeviceState, FabricSnapshot


class Severity(str, Enum):
    REGRESSION = "regression"   # piorou — reprova a mudança
    IMPROVEMENT = "improvement" # melhorou — só informa
    INFO = "info"               # mudou sem piorar


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
        """True quando é seguro seguir em frente."""
        return not self.regressions and not self.missing_devices

    def report(self) -> str:
        lines: list[str] = []
        if self.missing_devices:
            lines.append(f"✗ Sumiram do fabric: {', '.join(sorted(self.missing_devices))}")
        if self.new_devices:
            lines.append(f"· Novos no fabric: {', '.join(sorted(self.new_devices))}")
        lines.extend(str(f) for f in self.findings)
        if not lines:
            return "Nenhuma diferença entre os retratos."
        verdict = "APROVADO" if self.ok else "REPROVADO"
        return "\n".join(lines) + f"\n\nVeredito: {verdict}"


# Métricas em que "maior é melhor". Cair = regressão.
_HIGHER_IS_BETTER = (
    ("control_connections_up", "conexões de controle"),
    ("bfd_sessions_up", "sessões BFD"),
    ("omp_peers_up", "peers OMP"),
)


def _compare_device(before: DeviceState, after: DeviceState) -> list[Finding]:
    findings: list[Finding] = []

    if before.reachable and not after.reachable:
        findings.append(
            Finding(after.system_ip, after.hostname, "alcançabilidade", "reachable",
                    "unreachable", Severity.REGRESSION)
        )
    elif not before.reachable and after.reachable:
        findings.append(
            Finding(after.system_ip, after.hostname, "alcançabilidade", "unreachable",
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
            Finding(after.system_ip, after.hostname, "peers BFD perdidos", sorted(lost_peers),
                    [], Severity.REGRESSION)
        )

    return findings


def compare(before: FabricSnapshot, after: FabricSnapshot) -> SnapshotDiff:
    """Compara dois retratos e emite um veredito."""
    diff = SnapshotDiff()
    diff.missing_devices = sorted(before.devices.keys() - after.devices.keys())
    diff.new_devices = sorted(after.devices.keys() - before.devices.keys())

    for system_ip in sorted(before.devices.keys() & after.devices.keys()):
        diff.findings.extend(_compare_device(before.devices[system_ip], after.devices[system_ip]))

    return diff
