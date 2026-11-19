# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-11-19

### Changed — BREAKING

- Renamed the package and repository from `pysos_simulate` to
  `pysos_coordinate`. The old name implied mission coordination and
  simulation, but the package only starts and stops instances, allocates
  ports, and owns clock policy; it never simulates anything.
- **Breaking:** the import path changed from `pysos_simulate` to
  `pysos_coordinate`. Downstream imports must be updated.
- **Breaking:** the console script changed from `pysos-simulate` to
  `pysos-coordinate`. The old entry point no longer exists.
- No compatibility shims are provided; this is a clean cut-over.
- Behaviour is unchanged: same manifest schema, same API surface, same
  exit codes, same CLI options.

## [0.1.0] - 2026-11-19

### Added

- `Endpoint` with JSON roundtrip and `Endpoint.udp(port)`.
- `EntityRef` local duplicate-free reference (`site`, `application`, `entity`,
  `marking`), matching `pysos_interop` by field name without importing it.
- `InstanceSpec` and `FederationSpec` with JSON roundtrip and `validate()`:
  unique instance names, non-empty commands, unique endpoints, schema check.
- `TimingPolicy.WALL_CLOCK` as the only timing policy; anything else is
  rejected. Lock-step co-simulation is an explicit non-goal.
- `PortAllocator(base=5501, stride=2)` with deterministic allocation,
  idempotent per instance, reservation and manifest conflict detection.
- `Federation` supervisor: `start`, `wait`, `stop` (SIGTERM then SIGKILL),
  `status`, `logs`, and `run` returning `FederationResult`. stdout/stderr are
  captured per instance under a caller-supplied or temporary log directory.
- CLI `pysos-simulate {run,validate,ports}` with `--duration`, `--log-dir`,
  and `--json`; exit code 1 for invalid manifests, collisions, non-zero child
  exits, and timed-out runs.
- Standard-library test suite covering spec, allocator, supervisor, and CLI.
