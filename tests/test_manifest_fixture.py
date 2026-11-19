"""The checked-in manifest produced by pysos_sysml stays readable here.

The fixture is a mirror of ``pysos_sysml/tests/fixtures/two_instances.manifest.json``.
It lets this repository protect the contract without importing the setup layer.
"""

from __future__ import annotations

import json
from pathlib import Path

from pysos_coordinate import Federation, FederationSpec

FIXTURE = Path(__file__).parent / "fixtures" / "two_instances.manifest.json"


def test_checked_in_sysml_manifest_parses_and_validates() -> None:
    spec = FederationSpec.from_json(json.loads(FIXTURE.read_text(encoding="utf-8")))

    assert spec.name == "TwoInstances"
    assert spec.schema == 1
    assert spec.timing.value == "wall_clock"
    assert [instance.name for instance in spec.instances] == ["alpha", "beta"]
    assert spec.instances[0].command == ["alpha-engine", "--mode", "fast"]
    assert spec.instances[0].entities[0].site == "1"
    assert spec.instances[0].telemetry[0].port == 5551

    # Constructor validation only: no process is launched.
    Federation(spec)
