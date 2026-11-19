# Layers

The package is a shallow stack. Data types do not import behaviour, behaviour
does not import the CLI, and nothing below the CLI prints.

```
cli.py            argparse, file IO, JSON output, exit codes
   |
supervisor.py     Popen lifecycle, signals, status, logs
   |
ports.py          deterministic allocation, reservations, conflicts
   |
spec.py           FederationSpec / InstanceSpec, JSON, validate()
   |        \
timing.py   endpoint.py / entity.py     value types, no package imports
```

## Rules

| Layer | May import | Must not import |
| --- | --- | --- |
| `endpoint`, `entity`, `timing` | stdlib | anything else in the package |
| `spec` | value types | `ports`, `supervisor`, `cli` |
| `ports` | `endpoint`, `spec` | `supervisor`, `cli` |
| `supervisor` | `spec` | `ports`, `cli` |
| `cli` | everything public | private helpers of other modules |

## Consequences

- Value types are usable on their own: a manifest can be built, serialised, and
  validated without ever spawning a process.
- The supervisor is not a port allocator. It consumes whatever endpoints the
  manifest declares; callers that want allocation run `PortAllocator` first and
  feed the result into the manifest.
- There is no engine adapter layer, by design. A future integration with
  `pysos_interop` goes in its own module above the value types and below the
  CLI, and must stay optional.

## Module map

| Module | Owns |
| --- | --- |
| `endpoint` | host/port identity, JSON, `udp` convenience |
| `entity` | site/application/entity/marking identity |
| `timing` | the `TimingPolicy` enum and string coercion |
| `spec` | manifest shape, defaults, validation, JSON roundtrip |
| `ports` | base/stride band, reservations, conflict report |
| `supervisor` | spawn, wait, stop, status, logs, `run` |
| `cli` | `run`, `validate`, `ports`, exit codes |
