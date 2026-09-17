"""Automation toolkit for Cisco Catalyst SD-WAN.

Built one lesson at a time during the bootcamp. Each module maps to a stage:

    vault        →  module 1  — credentials out of the code
    client       →  module 3  — an authenticated session to the Manager
    inventory    →  module 3  — who is who in the fabric
    state        →  module 4  — an operational state snapshot
    diff         →  module 4  — the judge of the change
    tasks        →  module 4  — the asynchronous model
    configgroup  →  module 4  — declarative change
    datamodel    →  module 6  — the change as reviewable data

Modules 1 and 3 are the ones you write yourself (`vault.py` and `client.py`);
the rest are written on top of them, and they are short precisely because
those two exist.
"""

from .client import AuthenticationError, SDWANClient, SDWANError
from .datamodel import (
    DataModelError,
    FabricData,
    load_data_model,
    render_tfvars,
    semantic_checks,
    write_tfvars,
)
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
    "FabricData", "load_data_model", "semantic_checks", "render_tfvars",
    "write_tfvars", "DataModelError",
    "__version__",
]
