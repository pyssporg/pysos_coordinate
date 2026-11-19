# pysos-simulate

Set up and supervise a **federation** of independently launched simulation
instances. Each instance may be a different engine; the federation only needs
to know how to start it, where it listens, and how long it may live.

`pysos_simulate` owns **process, ports, timing policy, and status**. It does not
run models and knows nothing about SSP, FMU, DIS, or SysML.

```bash
pip install pysos-simulate
pysos-simulate validate federation.json
pysos-simulate ports federation.json
pysos-simulate run federation.json --duration 10 --log-dir logs
```

## Manifest

```json
{
  "schema": 1,
  "name": "demo",
  "timing": "wall_clock",
  "instances": [
    {
      "name": "alpha",
      "command": ["python", "-m", "alpha_engine", "--telemetry", "5601"],
      "cwd": "engines/alpha",
      "env": {"ALPHA_MODE": "fast"},
      "entities": [
        {"site": "lab", "application": "alpha", "entity": "aircraft", "marking": "unclassified"}
      ],
      "telemetry": [{"host": "127.0.0.1", "port": 5601}],
      "control": [{"host": "127.0.0.1", "port": 5602}],
      "startup_timeout": 30.0
    }
  ]
}
```

`name`, `instances`, `command`, and each instance `name` are required;
everything else has a default (`schema` defaults to `1`). Commands are argv
lists and are executed without a shell.

## Public API

| Module | Surface |
| --- | --- |
| `pysos_simulate.endpoint` | `Endpoint(host, port)`, `Endpoint.udp(port)` |
| `pysos_simulate.entity` | `EntityRef(site, application, entity, marking)` |
| `pysos_simulate.spec` | `InstanceSpec`, `FederationSpec`, `SpecError` |
| `pysos_simulate.ports` | `PortAllocator(base=5501, stride=2)` |
| `pysos_simulate.supervisor` | `Federation`, `InstanceStatus`, `FederationResult` |
| `pysos_simulate.timing` | `TimingPolicy.WALL_CLOCK` |

```python
from pathlib import Path

from pysos_simulate import FederationSpec, Federation

spec = FederationSpec.from_json(data)          # validates on the way in
result = Federation(spec, log_dir=Path("logs")).run(duration=10.0)
assert result.ok, result.exit_codes
```

## Endpoints

`PortAllocator.allocate(instance)` returns `(telemetry, control)` from a fixed
band: `base + i * stride` and `base + i * stride + 1`, where `i` is allocation
order. The mapping is deterministic and idempotent per instance name.
`reserve(endpoint)` and `reserve_spec(spec)` protect ports already in use;
`conflicts(spec)` reports overlaps before anything is launched.

## Timing

Only `TimingPolicy.WALL_CLOCK` exists at 0.1.0. Each instance advances on its
own clock and the supervisor bounds its lifetime. Deterministic lock-step
co-simulation — a master algorithm negotiating time advances — is an explicit
non-goal of this package; it belongs to whoever owns the federation protocol.

## Non-goals

- Running models, engines, or protocols (SSP, FMI/FMU, DIS, SysML).
- Time synchronisation or a master algorithm.
- Retries, campaign scheduling, or acceptance decisions.
- Third-party runtime dependencies.

## Relation to the family

`pysos_simulate` is the second package in the `pysos_*` family, after
`pysos_standard`. It has no dependency on `pyssp_*` packages. `EntityRef` is
currently a local duplicate of the `pysos_interop` reference: the two agree by
field name (`site`, `application`, `entity`, `marking`), and a future release
may consolidate them once the dependency is acceptable.

## License

MIT.
