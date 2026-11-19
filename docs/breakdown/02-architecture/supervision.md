# Supervision

`Federation(spec, log_dir=None)` is the only stateful object. It validates the
spec in the constructor, so an invalid manifest cannot reach `start()`.

## Lifecycle

1. **`start()`** — create `log_dir` if needed (a temp directory when the caller
   supplied none, kept after the run), then spawn each instance in manifest
   order with `subprocess.Popen(argv, cwd=..., env=..., shell=False,
   stdin=DEVNULL, stdout=<name>.stdout.log, stderr=<name>.stderr.log)`.
   Environment is `{**os.environ, **instance.env}`, so `PATH` still resolves and
   the instance's entries win. If any spawn raises `OSError` (missing executable,
   missing `cwd`), the already started instances are stopped and
   `LaunchError` propagates. Nothing is skipped silently.
2. **`wait(timeout=None)`** — poll every child every 20 ms until all have exited
   or the deadline passes. Returns `{name: exit_code | None}`; `None` means still
   running. A single absolute deadline is used, so N children under one timeout
   cannot serialise into N × timeout.
3. **`stop(grace=5.0)`** — SIGTERM every running child, wait up to `grace`
   seconds in total, then SIGKILL the survivors and reap them. Idempotent.
4. **`run(duration=None)`** — `start()`, then `wait(duration)`; if the deadline
   left children running, set `timed_out=True` and `stop()`. The `finally` branch
   stops anything still alive, so a caller exception cannot orphan processes.
   Returns `FederationResult(exit_codes, started_at, duration_s, timed_out,
   log_dir, statuses)`; `result.ok` is true only when every code is 0.

`Federation` is also a context manager: entering starts, leaving stops.

## What the supervisor does not do

- **No readiness handshake.** `startup_timeout` is part of the manifest and is
  validated, but 0.1.0 does not probe an instance for readiness. `start()`
  returns as soon as `Popen` succeeds. This is the most likely field to gain
  meaning in a later release (log or port readiness, bounded by that timeout).
- **No time synchronisation.** `TimingPolicy.WALL_CLOCK` means each instance
  advances on its own clock; the supervisor only bounds lifetime. Lock-step
  co-simulation is an explicit non-goal.
- **No process groups.** Signals go to the direct child (`terminate()` /
  `kill()`). A child that forks grandchildren is responsible for its own
  descendants; `start_new_session`/`killpg` is deliberately not used.
- **No restart policy.** One launch per instance. A non-zero exit is data, not a
  trigger for retry.

## Status and logs

`status()` returns `InstanceStatus(name, pid, running, exit_code, started_at)`
in manifest order. `started_at` is a wall-clock POSIX timestamp recorded
immediately after `Popen`; `exit_code` follows `Popen` semantics (negative for
death by signal). `logs()` returns `{name: {"stdout": Path, "stderr": Path}}`,
empty before `start()`. File names are the instance name with anything outside
`[A-Za-z0-9_.-]` replaced by `_`.
