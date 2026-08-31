"""Automation toolkit for Cisco Catalyst SD-WAN.

Built one lesson at a time during the bootcamp. Each module maps to a stage:

    vault        →  module 1  — credentials out of the code
    client       →  module 1  — an authenticated session to the Manager
    inventory    →  module 1  — who is who in the fabric
    state        →  module 2  — an operational state snapshot
    diff         →  module 2  — the judge of the change
    tasks        →  module 3  — the asynchronous model
    configgroup  →  module 3  — declarative change
"""

from .client import AuthenticationError, SDWANClient, SDWANError
from .diff import Severity, SnapshotDiff, compare
from .inventory import Device, get_controllers, get_devices, get_edges
from .state import FabricSnapshot, take_snapshot
from .tasks import TaskFailed, TaskResult, TaskTimeout, wait_for_task
from .vault import CredentialsError, ManagerCredentials, load_credentials

__version__ = "1.0.0"

__all__ = [
    "SDWANClient", "SDWANError", "AuthenticationError",
    "load_credentials", "ManagerCredentials", "CredentialsError",
    "Device", "get_devices", "get_edges", "get_controllers",
    "FabricSnapshot", "take_snapshot",
    "compare", "SnapshotDiff", "Severity",
    "wait_for_task", "TaskResult", "TaskFailed", "TaskTimeout",
    "__version__",
]
