"""Supervise a federation of independently launched simulation instances.

``pysos_coordinate`` owns process, ports, timing policy, and status. It does not
run models and knows nothing about SSP, FMU, DIS, or SysML.
"""

from __future__ import annotations

from .endpoint import Endpoint
from .entity import EntityRef
from .ports import PortAllocator, UnixAllocator
from .spec import FederationSpec, InstanceSpec, SpecError
from .supervisor import (
    Federation,
    FederationResult,
    InstanceStatus,
    LaunchError,
    SupervisorError,
)
from .timing import TimingPolicy

__version__ = "0.4.0"

__all__ = [
    "Endpoint",
    "EntityRef",
    "Federation",
    "FederationResult",
    "FederationSpec",
    "InstanceSpec",
    "InstanceStatus",
    "LaunchError",
    "PortAllocator",
    "SpecError",
    "SupervisorError",
    "TimingPolicy",
    "UnixAllocator",
    "__version__",
]
