from __future__ import annotations

import sys

import pysos_simulate
from pysos_simulate import (
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
)


def test_version_and_public_surface() -> None:
    assert pysos_simulate.__version__ == "0.1.0"
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
    )
    for value in values:
        assert value is not None
    assert TimingPolicy.WALL_CLOCK.value == "wall_clock"
    assert set(pysos_simulate.__all__) == {value.__name__ for value in values} | {
        "__version__"
    }


def test_core_imports_nothing_third_party() -> None:
    import pysos_simulate.cli
    import pysos_simulate.supervisor

    assert pysos_simulate.cli and pysos_simulate.supervisor
    third_party = {"numpy", "pandas", "pydantic", "requests", "yaml"} & set(sys.modules)
    assert not third_party, f"core imported {sorted(third_party)}"
