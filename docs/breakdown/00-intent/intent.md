---
id: INFO-001
type: info
title: Intent
summary: "Why pysos_coordinate exists: supervise a federation of independently launched simulation instances; processes, ports, timing, and status, nothing else"
date: 2026-11-19
status: current
---

# Intent

## Purpose

`pysos_coordinate` sets up and supervises a **federation** of independently
launched simulation instances, each of which may be a different engine. It owns
**process, ports, timing policy, and status**. It does not run models itself and
knows nothing about SSP, FMU, FMI, DIS, or SysML.

## Scope

| Belongs here | Belongs elsewhere |
| --- | --- |
| federation manifest (`FederationSpec`, `InstanceSpec`) | package/archive formats (`pysos_standard`) |
| process launch, lifetime, signals | engine execution inside a model (`pyssp_simulate` and engines) |
| deterministic port allocation and collision checks | wire protocols and payloads (`pysos_interop`, future) |
| timing policy declaration | time synchronisation and master algorithms |
| status, exit codes, captured logs | measurement, judgment, acceptance |

## Commitments

- **Processes, not threads.** Every instance is an OS process launched with
  `subprocess.Popen`, without a shell.
- **No engine knowledge, no protocol knowledge.** A participant is an argv, a
  working directory, an environment, some `EntityRef`s, and some endpoints.
- **Explicit timing policy.** `TimingPolicy.WALL_CLOCK` is the only policy at
  0.2.0. Anything else is rejected with a clear error, never ignored.
- **Deterministic ports.** Allocation depends only on base, stride, and call
  order; reserving a manifest's declared endpoints prevents collisions.
- **Explicit failure.** Invalid specs raise `SpecError`, launch failures raise
  `LaunchError`, non-zero child exits are reported and drive the CLI exit code.
- **Standard library only.** The base install has no runtime dependencies.

## Non-goals

- Deterministic lock-step co-simulation or any master time-advance algorithm.
- Model execution, SSP XML, FMU import, DIS, SysML, or engine adapters.
- Payload, transport, or discovery protocols beyond host/port endpoints.
- Retries, campaign scheduling, measurement, or acceptance decisions.
- Depending on `pyssp_*`; `pysos_interop` integration is deferred.

## Success

A caller can describe a heterogeneous federation in one JSON manifest, validate
it before launch, see the exact ports each instance will use, start the
processes, bound their lifetime, stop them without orphans on the normal path,
and read back exit codes, timing, and captured logs.
