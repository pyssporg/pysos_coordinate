# AGENTS

## Vision first (required)

Before you read code, edit files, or plan a change, read the project vision:

**`docs/breakdown/00-intent/intent.md`**

It states why this repository exists, what it commits to, and what it refuses to
become. It is the first document to read, not a reference of last resort.

- Read it in full before making any change to code, tests, docs, or artifacts.
- Judge every proposed change against it. If a change conflicts with the vision,
  its commitments, goals, or non-goals, stop and surface the conflict; do not
  implement it silently.
- If the work shows the long-term direction is wrong, change the vision
  deliberately first, then the code. Never let the repository drift away from
  its stated intent.

## Rules

1. **Don't assume. Surface tradeoffs.** If a contract is ambiguous, stop and say
   so rather than picking a behaviour silently.
2. **Minimum code that solves the problem.** Nothing speculative.
3. **Touch only what you must.** Clean up only your own mess.
4. **Define success criteria and verify.**

## Repository focus

`pysos_simulate` sets up and supervises a federation of independently launched
simulation instances and reports process status. Each instance may use a
different engine. The package owns process, ports, timing policy, and status.
It owns no model semantics.

- `src/pysos_simulate/` is the implementation; `__init__` is the public surface.
- `pysos-simulate` (module `pysos_simulate.cli`) is the only CLI.
- `docs/breakdown/` records intent and architecture; it is not generated docs.

## Hard constraints

- **No engine knowledge.** This package never imports or knows about SSP, FMU,
  FMI, DIS, SysML, Modelica, or any specific simulator.
- **No protocol knowledge.** Endpoints are host/port pairs. Payloads, encodings,
  discovery, and wire formats are out of scope.
- **Explicit timing policy.** `TimingPolicy.WALL_CLOCK` is the only supported
  policy at 0.1.0. A manifest declaring anything else is rejected with a clear
  error. Deterministic lock-step co-simulation and any master algorithm remain
  explicit non-goals.
- **Processes, not threads.** Instances are launched with `subprocess.Popen`;
  the supervisor never runs an engine in-process.
- **No shell.** Commands are argv lists passed with `shell=False`. A command is
  never a string that a shell parses.
- **Standard library only at runtime.** `dependencies = []` is a commitment.
- **No dependency on `pyssp_*`.** Sibling packages may be integrated later
  through public modules, never imported from internals, and never required.
- **`EntityRef` is local at 0.1.0.** It duplicates the `pysos_interop` shape by
  field name on purpose; do not import `pysos_interop` yet.
- **Failure is explicit.** Invalid manifests raise `SpecError`; launch failures
  raise `LaunchError`; the supervisor never silently skips an instance.

## Code guidelines

- Keep argv lists, `Path` objects, and plain dataclasses at the borders.
- Prefer deterministic, testable behaviour: same manifest and call order, same
  ports and the same result shape.
- Tests are fast and standard-library only; child processes are
  `sys.executable -c` snippets, never engines.
- Run `ruff check src tests` and `python -m pytest` before claiming success.
