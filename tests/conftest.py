"""Fixtures: a fake Manager, with payloads in the real shape.

This exists so you can validate your code without the lab being up, without
waiting for your turn in the class queue, and with no risk of writing to the
fabric.
"""

import pytest

from sdwan_toolkit.vault import ManagerCredentials

BASE_URL = "https://manager.example.lab"


@pytest.fixture
def credentials():
    return ManagerCredentials(url=BASE_URL, username="automation", password="s3cr3t")


@pytest.fixture
def device_payload():
    """The real shape of /dataservice/device — note the hyphenated keys."""
    return [
        {
            "deviceId": "10.255.255.2", "system-ip": "10.255.255.2",
            "host-name": "Manager-1", "personality": "vmanage",
            "reachability": "reachable", "site-id": "1", "state": "green",
            "uuid": "1111-1111", "device-model": "vmanage",
        },
        {
            "deviceId": "10.255.255.3", "system-ip": "10.255.255.3",
            "host-name": "Controller-1", "personality": "vsmart",
            "reachability": "reachable", "site-id": "1", "state": "green",
            "uuid": "2222-2222", "device-model": "vsmart",
        },
        {
            "deviceId": "10.255.255.11", "system-ip": "10.255.255.11",
            "host-name": "Site1-Edge1", "personality": "vedge",
            "reachability": "reachable", "site-id": "101", "state": "green",
            "uuid": "3333-3333", "device-model": "vedge-C8000V",
        },
        {
            "deviceId": "10.255.255.12", "system-ip": "10.255.255.12",
            "host-name": "Site2-Edge1", "personality": "vedge",
            "reachability": "unreachable", "site-id": "102", "state": "red",
            "uuid": "4444-4444", "device-model": "vedge-C8000V",
        },
    ]


@pytest.fixture
def bfd_payload():
    return [
        {"system-ip": "10.255.255.12", "state": "up", "color": "mpls", "site-id": "102"},
        {"system-ip": "10.255.255.13", "state": "up", "color": "biz-internet", "site-id": "103"},
        {"system-ip": "10.255.255.14", "state": "down", "color": "mpls", "site-id": "104"},
    ]
