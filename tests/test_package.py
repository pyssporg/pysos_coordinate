from __future__ import annotations

import sys

import pysos_coordinate
from pysos_coordinate import (
    Endpoint,
    EntityRef,
    Federation,
    FederationResult,
    FederationSpec,
    InstanceSpec,
    InstanceStatus,
    LaunchError,
    PortAllocator,
    SpecError,
    SupervisorError,
    TimingPolicy,
    UnixAllocator,
)


def test_version_and_public_surface() -> None:
    assert pysos_coordinate.__version__ == "0.3.0"
    values = (
        Endpoint,
        EntityRef,
        Federation,
        FederationResult,
        FederationSpec,
        InstanceSpec,
        InstanceStatus,
        LaunchError,
        PortAllocator,
        SpecError,
        SupervisorError,
        TimingPolicy,
        UnixAllocator,
    )
    for value in values:
        assert value is not None
    assert TimingPolicy.WALL_CLOCK.value == "wall_clock"
    assert set(pysos_coordinate.__all__) == {value.__name__ for value in values} | {
        "__version__"
    }


def test_core_imports_nothing_third_party() -> None:
    import pysos_coordinate.cli
    import pysos_coordinate.supervisor

    assert pysos_coordinate.cli and pysos_coordinate.supervisor
    third_party = {"numpy", "pandas", "pydantic", "requests", "yaml"} & set(sys.modules)
    assert not third_party, f"core imported {sorted(third_party)}"
