"""Toolkit de automação para Cisco Catalyst SD-WAN.

Construído aula a aula durante o bootcamp. Cada módulo corresponde a uma etapa:

    vault        →  módulo 1  — credenciais fora do código
    client       →  módulo 1  — sessão autenticada no Manager
    inventory    →  módulo 1  — quem é quem no fabric
    state        →  módulo 2  — retrato do estado operacional
    diff         →  módulo 2  — o juiz da mudança
    tasks        →  módulo 3  — o modelo assíncrono
    configgroup  →  módulo 3  — mudança declarativa
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
