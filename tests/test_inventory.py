"""Inventory normalization."""

from sdwan_toolkit.inventory import Device, find_by_hostname, unreachable


def test_normalizes_hyphenated_keys(device_payload):
    edge = Device.from_api(device_payload[2])
    assert edge.hostname == "Site1-Edge1"
    assert edge.system_ip == "10.255.255.11"
    assert edge.site_id == "101"


def test_separates_edges_from_controllers(device_payload):
    devices = [Device.from_api(d) for d in device_payload]
    assert [d.hostname for d in devices if d.is_controller] == ["Manager-1", "Controller-1"]
    assert [d.hostname for d in devices if d.is_edge] == ["Site1-Edge1", "Site2-Edge1"]


def test_finds_the_unreachable_ones(device_payload):
    devices = [Device.from_api(d) for d in device_payload]
    assert [d.hostname for d in unreachable(devices)] == ["Site2-Edge1"]


def test_hostname_lookup_is_case_insensitive(device_payload):
    devices = [Device.from_api(d) for d in device_payload]
    assert find_by_hostname(devices, "site1-edge1").system_ip == "10.255.255.11"
    assert find_by_hostname(devices, "does-not-exist") is None


def test_to_dict_does_not_leak_the_raw_payload(device_payload):
    assert "raw" not in Device.from_api(device_payload[0]).to_dict()
