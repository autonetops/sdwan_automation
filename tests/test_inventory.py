"""Normalização do inventário."""

from sdwan_toolkit.inventory import Device, find_by_hostname, unreachable


def test_normaliza_chaves_com_hifen(device_payload):
    edge = Device.from_api(device_payload[2])
    assert edge.hostname == "Site1-Edge1"
    assert edge.system_ip == "10.255.255.11"
    assert edge.site_id == "101"


def test_separa_edge_de_controlador(device_payload):
    devices = [Device.from_api(d) for d in device_payload]
    assert [d.hostname for d in devices if d.is_controller] == ["Manager-1", "Controller-1"]
    assert [d.hostname for d in devices if d.is_edge] == ["Site1-Edge1", "Site2-Edge1"]


def test_encontra_os_inalcancaveis(device_payload):
    devices = [Device.from_api(d) for d in device_payload]
    assert [d.hostname for d in unreachable(devices)] == ["Site2-Edge1"]


def test_busca_por_hostname_ignora_caixa(device_payload):
    devices = [Device.from_api(d) for d in device_payload]
    assert find_by_hostname(devices, "site1-edge1").system_ip == "10.255.255.11"
    assert find_by_hostname(devices, "nao-existe") is None


def test_to_dict_nao_vaza_o_payload_cru(device_payload):
    assert "raw" not in Device.from_api(device_payload[0]).to_dict()
