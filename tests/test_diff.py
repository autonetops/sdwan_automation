"""O juiz da mudança. Testes puros — sem rede, rodam em qualquer lugar."""

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


def test_retratos_iguais_nao_geram_achados():
    diff = compare(_snapshot(), _snapshot())
    assert diff.findings == []
    assert diff.ok


def test_perder_sessao_bfd_e_regressao():
    diff = compare(_snapshot(), _snapshot(bfd_sessions_up=2))
    assert not diff.ok
    assert diff.regressions[0].metric == "sessões BFD"


def test_ganhar_sessao_bfd_nao_reprova():
    diff = compare(_snapshot(), _snapshot(bfd_sessions_up=6))
    assert diff.ok
    assert diff.findings[0].severity is Severity.IMPROVEMENT


def test_device_inalcancavel_e_regressao():
    diff = compare(_snapshot(), _snapshot(reachable=False))
    assert not diff.ok


def test_peer_bfd_perdido_e_regressao():
    diff = compare(_snapshot(), _snapshot(bfd_peers=["10.255.255.12"]))
    assert not diff.ok
    assert any("perdidos" in f.metric for f in diff.regressions)


def test_device_que_sumiu_reprova():
    depois = FabricSnapshot(taken_at="2026-01-01T01:00:00+00:00", devices={})
    diff = compare(_snapshot(), depois)
    assert not diff.ok
    assert diff.missing_devices == ["10.255.255.11"]


def test_snapshot_sobrevive_ao_disco(tmp_path):
    original = _snapshot()
    caminho = original.save(tmp_path / "antes.json")
    recarregado = FabricSnapshot.load(caminho)
    assert compare(original, recarregado).ok
