# Manifest

`pysos_coordinate` owns the execution-manifest schema. This leaf is the single
normative definition of schema **1**: top-level keys, instance fields, entity and
endpoint shapes, defaults, and compatibility rules. `pysos_sysml.lower` targets
this schema and must conform without importing `pysos_coordinate`; the manifest
dictionary is the only cross-package contract.

`FederationSpec.from_json` parses a manifest and calls `validate()`;
`validate()` can also be called on a hand-built spec. The same gate runs in the
CLI (`validate`, `run`, `ports`), so a bad manifest fails identically everywhere.

## Top level

| Key | Type | Default | Rule |
| --- | --- | --- | --- |
| `schema` | int | `1` | must be `1`; a bool is not an int |
| `name` | str | — | required, non-empty federation name |
| `timing` | str | `"wall_clock"` | `"wall_clock"` only at 0.3.0 |
| `instances` | list | — | required, at least one; names unique |

## Instance

| Key | Type | Default | Rule |
| --- | --- | --- | --- |
| `name` | str | — | required, non-empty, unique in the federation |
| `command` | list[str] | — | required, non-empty argv; never a shell string |
| `cwd` | str/null | `null` | relative paths resolve against the supervisor's cwd |
| `env` | object | `{}` | string→string, layered over `os.environ` |
| `entities` | list | `[]` | `EntityRef` objects; duplicate-free within the instance |
| `telemetry` | list | `[]` | `Endpoint` objects; unique across the federation |
| `control` | list | `[]` | `Endpoint` objects; unique across the federation |
| `startup_timeout` | number | `30.0` | positive; validated and reserved, not enforced at 0.3.0 |

### EntityRef

| Key | Type | Default | Rule |
| --- | --- | --- | --- |
| `site` | str | — | required, non-empty |
| `application` | str | — | required, non-empty |
| `entity` | str | — | required, non-empty |
| `marking` | str | `""` | any string, including empty |

All three identity fields are **text**, even when they originate as decimal
integers. A producer that authors integer ids emits their decimal spelling
(`2` becomes `"2"`) at this boundary. `marking` is part of the identity.

### Endpoint

| Key | Type | Default | Rule |
| --- | --- | --- | --- |
| `host` | str | — | required, non-empty |
| `port` | int | — | required, `1..65535`; a bool is not an int |

An endpoint is a host/port pair only. It carries no protocol, channel name, or
payload description.

## Metadata the supervisor consumes

The schema is the cross-package contract; the supervisor deliberately uses only
part of it. This table is normative for what `Federation` does with each field
at 0.3.0:

| Field | Verdict | What the supervisor does |
| --- | --- | --- |
| `schema` | `validated only` | Rejects anything but `1`; never forwarded to a child. |
| `name` (federation) | `validated only` | Required and non-empty; not used to name or address anything at runtime. |
| `timing` | `validated only` | Rejects anything but `wall_clock`; no clock is enforced or synchronised. |
| `instances` | `consumed` (launch) | Launched once each, in manifest order. |
| `name` (instance) | `consumed` (launch/status/process group) | Identifies the child, its log files, its status entry, and its process group. |
| `command` | `consumed` (launch) | Passed verbatim to `Popen` as argv with `shell=False`. |
| `cwd` | `consumed` (launch) | Passed to `Popen`; a missing directory fails the launch. |
| `env` | `pass-through to consumers` | Producer-owned and opaque to `pysos_coordinate`: the supervisor only merges it over `os.environ`; it never reads or interprets keys. Children read their own keys. |
| `entities` | `pass-through to consumers` | Shape and per-instance uniqueness are validated; the supervisor never acts on them. |
| `telemetry` | `pass-through to consumers` | Shape and federation-wide uniqueness are validated; the supervisor never binds or connects them. |
| `control` | `pass-through to consumers` | Shape and federation-wide uniqueness are validated; the supervisor never binds or connects them. |
| `startup_timeout` | `validated only` | Validated as a positive number and **reserved**: it is not yet a readiness gate, so `start()` returns as soon as `Popen` succeeds. |

`EntityRef` and `Endpoint` subfields are likewise validated on the way in and
otherwise passed through; only an instance's own `name`, `command`, and `cwd`
change what the supervisor does at runtime.

## Compatibility rules

1. **Schema 1 is current and in use.** A structural change, a field rename, a
   type change, or a change in meaning bumps `schema`; the reader rejects every
   value other than `1` explicitly and never guesses.
2. **Required versus optional.** A conforming producer emits every key in the
   tables above, including defaults; a consumer applies the listed defaults when
   an optional key is absent. `name` and `instances` are required at the top
   level; `name` and `command` are required per instance.
3. **Types are exact.** JSON strings are strings, JSON integers are integers,
   and JSON numbers are numbers. Entity identities are strings even when they
   look numeric.
4. **`command` is argv.** The supervisor passes it to `subprocess.Popen` with
   `shell=False`. A producer that starts from one authored command string must
   tokenize it itself without invoking a shell; it must not put the string in
   `command`.
5. **Unknown keys are not part of the contract.** The 0.3.0 reader ignores
   unrecognised keys so an older consumer can read a newer document, but a
   conforming producer must not rely on that. Only keys defined here are
   emitted.
6. **Occurrence naming belongs to the producer.** The consumer only requires
   unique, non-empty instance names. `pysos_sysml` names multiplicity
   occurrences `<name>_1` … `<name>_N` and leaves a scalar instance at its bare
   name.
7. **Ownership.** Changes to this schema are made here first. Consumers conform
   to this leaf; they do not define a second contract.

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
      "entities": [{"site": "1", "application": "10", "entity": "1", "marking": ""}],
      "telemetry": [{"host": "127.0.0.1", "port": 5601}],
      "control": [{"host": "127.0.0.1", "port": 5602}],
      "startup_timeout": 30.0
    }
  ]
}
```

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

## Cross-repo fixtures

`tests/fixtures/two_instances.manifest.json` is a mirror of the manifest that
`pysos_sysml` emits for its two-instance fixture. This repository parses it
without importing `pysos_sysml`, and `pysos_sysml` runs the reverse round trip
through this package when its optional `[dev]` extra is installed.

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
