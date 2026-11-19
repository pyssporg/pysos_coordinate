# Manifest

A manifest is a single JSON object. `FederationSpec.from_json` parses it and
calls `validate()`; `validate()` can also be called on a hand-built spec. The
same gate runs in the CLI (`validate`, `run`, `ports`), so a bad manifest fails
identically everywhere.

## Shape

| Field | Type | Default | Rule |
| --- | --- | --- | --- |
| `schema` | int | `1` | must be `1` |
| `name` | str | — | non-empty federation name |
| `timing` | str | `"wall_clock"` | `"wall_clock"` only at 0.2.0 |
| `instances` | list | — | at least one; names unique |

Each instance:

| Field | Type | Default | Rule |
| --- | --- | --- | --- |
| `name` | str | — | non-empty, unique in the federation |
| `command` | list[str] | — | non-empty, argv only (never a shell string) |
| `cwd` | str/null | `null` | relative paths resolve against the supervisor's cwd |
| `env` | object | `{}` | string→string, layered over `os.environ` |
| `entities` | list | `[]` | `EntityRef`; duplicate-free within the instance |
| `telemetry` | list | `[]` | `Endpoint`; unique across the whole federation |
| `control` | list | `[]` | `Endpoint`; unique across the whole federation |
| `startup_timeout` | float | `30.0` | positive; validated, not enforced at 0.2.0 |

## Validation rules

In order, first failure wins:

1. schema is an int and equals `1`; federation name is non-empty.
2. timing coerces to `TimingPolicy` and is `WALL_CLOCK`; otherwise the error
   names lock-step co-simulation as an explicit non-goal.
3. at least one instance exists.
4. every instance validates on its own: name, argv, `cwd` type, env strings,
   positive `startup_timeout`, duplicate-free entities, endpoint types.
5. instance names are unique.
6. telemetry and control endpoints are unique across the federation, and no
   instance repeats an endpoint locally.

All endpoint-level problems found in one pass are collected into a single
`SpecError` joined by `"; "`; the earlier checks fail fast.

## Example

```json
{
  "schema": 1,
  "name": "demo",
  "timing": "wall_clock",
  "instances": [
    {
      "name": "alpha",
      "command": ["python", "-m", "alpha_engine"],
      "cwd": "engines/alpha",
      "env": {"ALPHA_MODE": "fast"},
      "entities": [{"site": "lab", "application": "alpha", "entity": "aircraft", "marking": ""}],
      "telemetry": [{"host": "127.0.0.1", "port": 5601}],
      "control": [{"host": "127.0.0.1", "port": 5602}]
    }
  ]
}
```

## Ports in the manifest

Declared endpoints are what the supervisor uses. `PortAllocator` is a helper for
callers that have not fixed ports yet:

```python
from pysos_coordinate import PortAllocator

allocator = PortAllocator()
for instance in spec.instances:
    telemetry, control = allocator.allocate(instance)
    instance.telemetry.append(telemetry)
    instance.control.append(control)
```

Allocation is `base + i * stride` / `+1` for allocation order `i`, idempotent
per instance name, skips reserved endpoints, and refuses a stride below 2.

## Versioning

`schema` gates structural change. `0.2.0` reads only schema `1`. A future
release that changes field meaning must bump the schema and keep a reader for
the old one, or reject it explicitly; it must not guess.
