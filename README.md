# pysos-coordinate

Set up and supervise a **federation** of independently launched simulation
instances. Each instance may be a different engine; the federation only needs
to know how to start it, where it listens, and how long it may live.

`pysos_coordinate` owns **process, ports, timing policy, and status**. It does not
run models and knows nothing about SSP, FMU, DIS, or SysML.

## Install

Python 3.10 or newer is required. The package has no runtime dependencies
beyond the standard library.

```bash
pip install pysos-coordinate                # published package
pip install -e ".[dev]"                     # this checkout, with tests and lint
pip install -e "repos/pysos_coordinate[dev]"  # from the workspace root
```

## Quickstart

Save the manifest below as `federation.json`, then run:

```bash
pysos-coordinate validate federation.json
pysos-coordinate ports federation.json
pysos-coordinate run federation.json --duration 10 --log-dir logs
```

From a source checkout, `tests/fixtures/two_instances.manifest.json` can be
used with `validate` and `ports`; its example engines are not installed, so it
is not launchable as-is. `python -m pysos_coordinate` is an equivalent entry
point when the console script is not on `PATH`.

## Manifest

```json
{
  "schema": 2,
  "name": "demo",
  "timing": "wall_clock",
  "instances": [
    {
      "name": "alpha",
      "command": ["python3", "-c", "print('alpha ready')"],
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
everything else has a default (`schema` defaults to `2`). Commands are argv
lists and are executed without a shell. The command above is a portable
placeholder that exits immediately; a real manifest names the engine's argv and
`cwd`. This package owns the contract; the
normative field-by-field definition is
[`docs/breakdown/02-architecture/manifest.md`](docs/breakdown/02-architecture/manifest.md).
`pysos_sysml` conforms to it without importing this package.

## Public API

| Module | Surface |
| --- | --- |
| `pysos_coordinate.endpoint` | `Endpoint(host, port)`, `Endpoint.udp(port)`, `Endpoint.unix(path)` |
| `pysos_coordinate.entity` | `EntityRef(site, application, entity, marking)` |
| `pysos_coordinate.spec` | `InstanceSpec`, `FederationSpec`, `SpecError` |
| `pysos_coordinate.ports` | `PortAllocator(base=5501, stride=2)`, `UnixAllocator(prefix="pysos")` |
| `pysos_coordinate.supervisor` | `Federation`, `InstanceStatus`, `FederationResult` |
| `pysos_coordinate.timing` | `TimingPolicy.WALL_CLOCK` |

```python
import json
from pathlib import Path

from pysos_coordinate import Federation, FederationSpec

data = json.loads(Path("federation.json").read_text(encoding="utf-8"))
spec = FederationSpec.from_json(data)          # validates on the way in
result = Federation(spec, log_dir=Path("logs")).run(duration=10.0)
assert result.ok, result.exit_codes
```

## Endpoints

An endpoint is either UDP (`host`/`port`) or a Unix domain socket (`path`):
an absolute filesystem path such as `/run/pysos/alpha.sock`, or a Linux
abstract name such as `@pysos-alpha`. Schema 2 adds Unix endpoints; schema 1
manifests remain readable and round-trip unchanged. UDP JSON keeps exactly
`{"host", "port"}`, while Unix JSON is `{"transport": "unix", "path": "..."}`.

```python
from pysos_coordinate import Endpoint

udp = Endpoint.udp(5601)
sock = Endpoint.unix("@pysos-alpha")     # or Endpoint.unix("/tmp/alpha.sock")
assert udp.address == "127.0.0.1:5601"
assert sock.address == "@pysos-alpha"
```

`PortAllocator.allocate(instance)` returns `(telemetry, control)` from a fixed
band: `base + i * stride` and `base + i * stride + 1`, where `i` is allocation
order. The mapping is deterministic and idempotent per instance name.
`reserve(endpoint)` and `reserve_spec(spec)` protect ports already in use;
`conflicts(spec)` reports overlaps before anything is launched.

`UnixAllocator.allocate(instance)` returns an abstract `@<prefix>-<name>` path,
lowercased and sanitized to `[a-z0-9-]`, capped well under the 108-byte
`sun_path` limit. It is deterministic and idempotent per instance name;
`reserve(endpoint)` and `reserve_spec(spec)` skip Unix paths already declared
or reserved, appending `-2`, `-3`, … when needed.

## Timing

Only `TimingPolicy.WALL_CLOCK` exists at 0.4.0. Each instance advances on its
own clock and the supervisor bounds its lifetime. Deterministic lock-step
co-simulation — a master algorithm negotiating time advances — is an explicit
non-goal of this package; it belongs to whoever owns the federation protocol.

## Non-goals

- Running models, engines, or protocols (SSP, FMI/FMU, DIS, SysML).
- Time synchronisation or a master algorithm.
- Retries, campaign scheduling, or acceptance decisions.
- Third-party runtime dependencies.

## Relation to the family

`pysos_coordinate` is part of the `pysos_*` family. It has no dependency on
`pyssp_*` packages. `EntityRef` is currently a local duplicate of the
`pysos_interop` reference: the two agree by field name (`site`, `application`,
`entity`, `marking`), and a future release may consolidate them once the
dependency is acceptable.

## Development

```bash
python -m pytest
ruff check src tests
```

Ruff is configured in `pyproject.toml` (line length 100, target `py310`).
Read [`AGENTS.md`](AGENTS.md) and the
[intent](docs/breakdown/00-intent/intent.md) before changing behaviour. The
normative manifest contract is
[`docs/breakdown/02-architecture/manifest.md`](docs/breakdown/02-architecture/manifest.md);
the module stack is in
[`docs/breakdown/02-architecture/layers.md`](docs/breakdown/02-architecture/layers.md).

## License

MIT.
