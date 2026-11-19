# Supervision

`Federation(spec, log_dir=None)` is the only stateful object. It validates the
spec in the constructor, so an invalid manifest cannot reach `start()`.

## Lifecycle

1. **`start()`** — create `log_dir` if needed (a temp directory when the caller
   supplied none, kept after the run), then spawn each instance in manifest
   order with `subprocess.Popen(argv, cwd=..., env=..., shell=False,
   start_new_session=True, stdin=DEVNULL, stdout=<name>.stdout.log,
   stderr=<name>.stderr.log)`. Each instance therefore leads its own session and
   process group. Environment is `{**os.environ, **instance.env}`, so `PATH`
   still resolves and the instance's entries win. If any spawn raises `OSError` (missing executable,
   missing `cwd`), the already started instances are stopped and
   `LaunchError` propagates. Nothing is skipped silently.
2. **`wait(timeout=None)`** — poll every child every 20 ms until all have exited
   or the deadline passes. Returns `{name: exit_code | None}`; `None` means still
   running. A single absolute deadline is used, so N children under one timeout
   cannot serialise into N × timeout.
3. **`stop(grace=5.0)`** — signal every running instance's **whole process
   group** (`os.killpg`, because `start_new_session=True` makes the child pid the
   group id): SIGTERM first, wait up to `grace` seconds in total, then SIGKILL
   the group. The direct child is still reaped, so its exit code stays `-15`
   when SIGTERM killed it and `-9` when SIGKILL did. Descendants the instance
   forked or exec'd cannot survive the stop. An already-gone group
   (`ProcessLookupError`/`PermissionError`) is treated as gone, not an error.
   Instances that exited before `stop()` are never signalled. Idempotent.
4. **`run(duration=None)`** — `start()`, then `wait(duration)`; if the deadline
   left children running, set `timed_out=True` and `stop()`. The `finally` branch
   stops anything still alive, so a caller exception cannot orphan processes.
   Returns `FederationResult(exit_codes, started_at, duration_s, timed_out,
   log_dir, statuses)`; `result.ok` is true only when every code is 0.

`Federation` is also a context manager: entering starts, leaving stops.

## What the supervisor does not do

- **No readiness handshake.** `startup_timeout` is part of the manifest and is
  validated, but it is **reserved**: 0.3.0 does not probe an instance for
  readiness. `start()` returns as soon as `Popen` succeeds. This is the most
  likely field to gain meaning in a later release (log or port readiness,
  bounded by that timeout).
- **No time synchronisation.** `TimingPolicy.WALL_CLOCK` means each instance
  advances on its own clock; the supervisor only bounds lifetime. Lock-step
  co-simulation is an explicit non-goal.
- **Process groups, not process trees.** Each instance is launched in its own
  session, and `stop()` signals that group, so descendants are covered. The
  supervisor does not track descendants individually, does not signal groups of
  instances that had already exited, and does not clean up a daemon that calls
  `setsid()` to leave the group deliberately.
- **No restart policy.** One launch per instance. A non-zero exit is data, not a
  trigger for retry.

## Status and logs

`status()` returns `InstanceStatus(name, pid, running, exit_code, started_at)`
in manifest order. `started_at` is a wall-clock POSIX timestamp recorded
immediately after `Popen`; `exit_code` follows `Popen` semantics (negative for
death by signal). `logs()` returns `{name: {"stdout": Path, "stderr": Path}}`,
empty before `start()`. File names are the instance name with anything outside
`[A-Za-z0-9_.-]` replaced by `_`.
