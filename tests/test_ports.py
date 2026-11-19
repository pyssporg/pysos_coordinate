from __future__ import annotations

import pytest

from pysos_coordinate.endpoint import Endpoint
from pysos_coordinate.ports import PortAllocator
from pysos_coordinate.spec import FederationSpec, InstanceSpec


def _instance(name: str, **kwargs) -> InstanceSpec:
    return InstanceSpec(name=name, command=["python"], **kwargs)


def test_allocation_is_deterministic_by_order() -> None:
    first = PortAllocator()
    second = PortAllocator()
    assert first.allocate("alpha") == (Endpoint.udp(5501), Endpoint.udp(5502))
    assert first.allocate("beta") == (Endpoint.udp(5503), Endpoint.udp(5504))
    assert second.allocate("alpha") == first.allocations["alpha"]
    assert second.allocate("beta") == first.allocations["beta"]
    assert first.allocations == second.allocations


def test_allocation_is_idempotent_per_instance() -> None:
    allocator = PortAllocator()
    pair = allocator.allocate(_instance("alpha"))
    assert allocator.allocate(_instance("alpha")) == pair
    assert allocator.allocations == {"alpha": pair}


def test_reserve_skips_taken_ports_and_rejects_duplicates() -> None:
    allocator = PortAllocator()
    allocator.reserve(Endpoint.udp(5501))
    with pytest.raises(ValueError, match="already reserved"):
        allocator.reserve(Endpoint.udp(5501))
    assert allocator.allocate("alpha") == (Endpoint.udp(5503), Endpoint.udp(5504))


def test_conflicts_report_duplicates_and_reservations() -> None:
    allocator = PortAllocator()
    allocator.reserve(Endpoint.udp(5701))
    spec = FederationSpec(
        "demo",
        [
            _instance("alpha", telemetry=[Endpoint.udp(5601)], control=[Endpoint.udp(5701)]),
            _instance("beta", telemetry=[Endpoint.udp(5601)]),
        ],
    )
    problems = allocator.conflicts(spec)
    assert any("reserved endpoint" in problem for problem in problems)
    assert any("share endpoint" in problem for problem in problems)


def test_reserve_spec_keeps_declared_ports_free() -> None:
    spec = FederationSpec(
        "demo", [_instance("alpha"), _instance("beta", telemetry=[Endpoint.udp(5501)])]
    )
    allocator = PortAllocator()
    allocator.reserve_spec(spec)
    assert allocator.allocate("beta") == (Endpoint.udp(5503), Endpoint.udp(5504))
    assert allocator.conflicts(spec) == []


def test_rejects_bad_bands() -> None:
    with pytest.raises(ValueError, match="stride"):
        PortAllocator(stride=1)
    with pytest.raises(ValueError, match="base"):
        PortAllocator(base=0)
    allocator = PortAllocator(base=65533, stride=2)
    allocator.allocate("first")
    with pytest.raises(OverflowError, match="exhausted"):
        allocator.allocate("second")
