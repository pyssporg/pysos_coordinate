# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-11-24

Unix domain socket endpoints and a runnable README quickstart.

### Added

- Unix domain socket endpoints: `Endpoint.unix(path)` for absolute paths and
  abstract `@name` addresses, schema 2 with UDP schema 1 still readable, and
  `UnixAllocator` for deterministic abstract names that skip reserved paths.

### Changed

- README install and quickstart are runnable as written: a self-contained
  manifest, `python -m pysos_coordinate` as an alternate entry point, and a note
  that the source-checkout fixture is not launchable because its engines are not
  installed.

## [0.3.0] - 2026-11-19

Process-group teardown and per-instance status in the run result.

### Added

- `FederationResult.to_json()` now includes `statuses`: one JSON-safe entry per
  instance with `name`, `pid`, `running`, `exit_code`, and `started_at`, so a
  run manifest can report process state per aircraft.
- `docs/breakdown/02-architecture/manifest.md` has a normative "Metadata the
  supervisor consumes" section: one row per schema field with its verdict
  (`consumed`, `validated only`, or `pass-through to consumers`), including that
  `startup_timeout` is validated and reserved and that `env` is opaque to
  `pysos_coordinate`.
- `docs/breakdown/02-architecture/supervision.md` documents the process-group
  stop semantics and repeats that `startup_timeout` is reserved.

### Changed

- Instances are launched with `start_new_session=True`, and `stop()` — plus the
  `run()` and context-manager stop paths that call it — signals the whole
  process group with `os.killpg` instead of the direct child only. A launcher
  that forks or execs a simulation child no longer leaves orphaned grandchildren
  or bound ports behind. The direct child is still reaped, so exit codes are
  unchanged: `-15` when SIGTERM killed it, `-9` when SIGKILL did. An
  already-gone or foreign group is treated as gone, never an error.

## [0.2.1] - 2026-11-19

Documentation-and-contract release: the execution manifest schema is now
specified in-repo (schema version 1, argv commands, string entity ids, top-level
name); no behaviour change. 0.2.0 was released before this contract was written
down.

### Added

- `docs/breakdown/02-architecture/manifest.md` is now the normative schema-1
  contract: every top-level and instance key, entity and endpoint shape,
  defaults, and compatibility rules.
- A checked-in mirror of the `pysos_sysml` two-instance lowering plus a test
  that parses and validates it here without importing the setup layer.

### Changed

- Documentation now states that `pysos_coordinate` owns the schema and that
  consumers conform without importing it. No code or behaviour changed.

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
