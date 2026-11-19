from __future__ import annotations

from pathlib import Path

import pytest

from pysos_simulate.endpoint import Endpoint
from pysos_simulate.entity import EntityRef
from pysos_simulate.spec import FederationSpec, InstanceSpec, SpecError
from pysos_simulate.timing import TimingPolicy


def _instance(name: str, **kwargs) -> InstanceSpec:
    return InstanceSpec(name=name, command=["python", "-c", "pass"], **kwargs)


def test_minimal_roundtrip() -> None:
    spec = FederationSpec("demo", [_instance("alpha")])
    payload = spec.to_json()
    assert payload["schema"] == 1
    assert payload["timing"] == "wall_clock"
    assert FederationSpec.from_json(payload) == spec


def test_full_roundtrip() -> None:
    spec = FederationSpec(
        "demo",
        [
            InstanceSpec(
                name="alpha",
                command=["engine", "--port", "5501"],
                cwd=Path("engines/alpha"),
                env={"MODE": "fast"},
                entities=[EntityRef("lab", "alpha", "aircraft", "secret")],
                telemetry=[Endpoint.udp(5601)],
                control=[Endpoint.udp(5602)],
                startup_timeout=12.5,
            )
        ],
    )
    payload = spec.to_json()
    assert payload["instances"][0]["cwd"] == "engines/alpha"
    restored = FederationSpec.from_json(payload)
    assert restored == spec
    assert restored.instances[0].cwd == Path("engines/alpha")
    assert restored.timing is TimingPolicy.WALL_CLOCK


def test_defaults() -> None:
    instance = InstanceSpec("alpha", ["python"])
    assert instance.cwd is None
    assert instance.env == {}
    assert instance.entities == []
    assert instance.telemetry == []
    assert instance.control == []
    assert instance.startup_timeout == 30.0


def test_rejects_duplicate_instance_names() -> None:
    spec = FederationSpec("demo", [_instance("alpha"), _instance("alpha")])
    with pytest.raises(SpecError, match="duplicate instance name"):
        spec.validate()


def test_rejects_empty_command() -> None:
    spec = FederationSpec("demo", [InstanceSpec("alpha", [])])
    with pytest.raises(SpecError, match="command must not be empty"):
        spec.validate()


def test_rejects_duplicate_endpoints() -> None:
    shared = Endpoint.udp(5601)
    spec = FederationSpec(
        "demo",
        [
            _instance("alpha", telemetry=[shared]),
            _instance("beta", control=[shared]),
        ],
    )
    with pytest.raises(SpecError, match="declared by both"):
        spec.validate()

    repeated = FederationSpec("demo", [_instance("alpha", control=[shared, shared])])
    with pytest.raises(SpecError, match="duplicate endpoint"):
        repeated.validate()


def test_rejects_unsupported_timing() -> None:
    payload = FederationSpec("demo", [_instance("alpha")]).to_json()
    payload["timing"] = "lockstep"
    with pytest.raises(SpecError, match="co-simulation"):
        FederationSpec.from_json(payload)


def test_rejects_unsupported_schema_and_empty_federation() -> None:
    with pytest.raises(SpecError, match="unsupported manifest schema"):
        FederationSpec("demo", [_instance("alpha")], schema=2).validate()
    with pytest.raises(SpecError, match="at least one instance"):
        FederationSpec("demo", []).validate()
    with pytest.raises(SpecError, match="timing policy"):
        FederationSpec("demo", [_instance("alpha")], timing="event").validate()  # type: ignore[arg-type]
