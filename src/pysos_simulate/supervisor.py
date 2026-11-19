"""Spawn, watch, and stop the processes that make up a federation.

The supervisor owns processes, ports, timing policy, and status. It owns no
model semantics: an instance is an argv, a working directory, an environment,
and a lifetime.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any

from .spec import FederationSpec

_SLEEP = 0.02
_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


class SupervisorError(RuntimeError):
    """The federation was driven out of order or cannot be driven at all."""


class LaunchError(SupervisorError):
    """One instance could not be spawned; already started instances were stopped."""


@dataclass(frozen=True, slots=True)
class InstanceStatus:
    """Snapshot of one instance.

    ``started_at`` is a wall-clock POSIX timestamp, ``None`` before launch.
    ``exit_code`` is ``None`` while running and negative when the process died
    from a signal (``Popen`` semantics).
    """

    name: str
    pid: int | None
    running: bool
    exit_code: int | None
    started_at: float | None

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "pid": self.pid,
            "running": self.running,
            "exit_code": self.exit_code,
            "started_at": self.started_at,
        }


@dataclass(frozen=True, slots=True)
class FederationResult:
    """Outcome of ``Federation.run``."""

    exit_codes: dict[str, int | None]
    started_at: float
    duration_s: float
    timed_out: bool
    log_dir: Path | None = None
    statuses: tuple[InstanceStatus, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        """True when every instance exited with status 0."""
        return bool(self.exit_codes) and all(code == 0 for code in self.exit_codes.values())

    def to_json(self) -> dict[str, Any]:
        return {
            "exit_codes": dict(self.exit_codes),
            "started_at": self.started_at,
            "duration_s": self.duration_s,
            "timed_out": self.timed_out,
            "log_dir": None if self.log_dir is None else str(self.log_dir),
        }


class Federation:
    """Supervise one ``FederationSpec``.

    ``log_dir`` is created if absent. When it is ``None`` a temporary directory
    is created at ``start()`` and kept after the run so the caller can inspect
    it. Every instance gets ``<name>.stdout.log`` and ``<name>.stderr.log``.
    """

    def __init__(self, spec: FederationSpec, *, log_dir: Path | str | None = None) -> None:
        self.spec = spec
        self.spec.validate()
        self.log_dir: Path | None = None if log_dir is None else Path(log_dir)
        self._procs: dict[str, subprocess.Popen[bytes]] = {}
        self._log_paths: dict[str, tuple[Path, Path]] = {}
        self._handles: list[IO[bytes]] = []
        self._started_at: dict[str, float] = {}
        self._exit_codes: dict[str, int | None] = {}
        self._started = False

    # -- lifecycle -------------------------------------------------------
    def start(self) -> Federation:
        if self._started:
            raise SupervisorError("federation has already been started")
        if self.log_dir is None:
            self.log_dir = Path(tempfile.mkdtemp(prefix="pysos-simulate-"))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._started = True
        try:
            for instance in self.spec.instances:
                self._spawn(instance)
        except OSError as exc:
            self.stop()
            raise LaunchError(f"instance failed to launch: {exc}") from exc
        return self

    def _spawn(self, instance) -> None:
        stem = _SAFE.sub("_", instance.name) or "instance"
        out_path = self.log_dir / f"{stem}.stdout.log"  # type: ignore[union-attr]
        err_path = self.log_dir / f"{stem}.stderr.log"  # type: ignore[union-attr]
        cwd = None if instance.cwd is None else os.fspath(instance.cwd)
        if cwd is not None and not Path(cwd).is_dir():
            raise LaunchError(f"instance {instance.name!r}: cwd does not exist: {cwd}")
        env = {**os.environ, **instance.env}
        out = open(out_path, "wb")
        err = open(err_path, "wb")
        try:
            proc = subprocess.Popen(  # noqa: S603 - argv, shell=False, by design
                instance.command,
                cwd=cwd,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                shell=False,
            )
        except OSError:
            out.close()
            err.close()
            raise
        self._handles.extend((out, err))
        self._procs[instance.name] = proc
        self._log_paths[instance.name] = (out_path, err_path)
        self._started_at[instance.name] = time.time()

    def _require_started(self) -> None:
        if not self._started:
            raise SupervisorError("federation has not been started")

    def _snapshot_codes(self) -> dict[str, int | None]:
        self._exit_codes = {name: proc.returncode for name, proc in self._procs.items()}
        return dict(self._exit_codes)

    def _close_handles(self) -> None:
        for handle in self._handles:
            try:
                handle.close()
            except OSError:  # pragma: no cover - defensive
                pass
        self._handles.clear()

    def close(self) -> None:
        self._close_handles()

    # -- observation -----------------------------------------------------
    def wait(self, timeout: float | None = None) -> dict[str, int | None]:
        """Wait for every instance to exit, or until *timeout* seconds pass.

        Returns the current exit-code map; entries still running are ``None``.
        """
        self._require_started()
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be non-negative or None")
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            if all(proc.poll() is not None for proc in self._procs.values()):
                break
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                time.sleep(min(_SLEEP, remaining))
            else:
                time.sleep(_SLEEP)
        codes = self._snapshot_codes()
        if all(code is not None for code in codes.values()):
            self._close_handles()
        return codes

    def status(self) -> list[InstanceStatus]:
        """One status per instance, in manifest order."""
        result: list[InstanceStatus] = []
        for instance in self.spec.instances:
            proc = self._procs.get(instance.name)
            code = None if proc is None else proc.poll()
            result.append(
                InstanceStatus(
                    name=instance.name,
                    pid=None if proc is None else proc.pid,
                    running=proc is not None and code is None,
                    exit_code=code,
                    started_at=self._started_at.get(instance.name),
                )
            )
        return result

    def logs(self) -> dict[str, dict[str, Path]]:
        """Paths to captured stdout/stderr per instance; empty before ``start``."""
        return {
            name: {"stdout": paths[0], "stderr": paths[1]}
            for name, paths in self._log_paths.items()
        }

    # -- teardown --------------------------------------------------------
    def stop(self, grace: float = 5.0) -> dict[str, int | None]:
        """SIGTERM every running instance, wait up to *grace*, then SIGKILL.

        Idempotent: calling it again returns the codes already recorded.
        """
        if not self._started:
            raise SupervisorError("federation has not been started")
        if grace < 0:
            raise ValueError("grace must be non-negative")
        running = [proc for proc in self._procs.values() if proc.poll() is None]
        for proc in running:
            try:
                proc.terminate()
            except ProcessLookupError:  # pragma: no cover - race
                pass
        deadline = time.monotonic() + grace
        while running:
            running = [proc for proc in running if proc.poll() is None]
            if not running or time.monotonic() >= deadline:
                break
            time.sleep(_SLEEP)
        for proc in running:
            try:
                proc.kill()
            except ProcessLookupError:  # pragma: no cover - race
                pass
        for proc in self._procs.values():
            try:
                proc.wait(timeout=grace + 5.0)
            except subprocess.TimeoutExpired:  # pragma: no cover - defensive
                pass
        codes = self._snapshot_codes()
        self._close_handles()
        return codes

    def run(self, duration: float | None = None) -> FederationResult:
        """Start, run for *duration* (or until all exit), stop, and report.

        ``timed_out`` is true only when the duration elapsed while at least one
        instance was still running. Instances are always stopped on the way out.
        """
        if duration is not None and duration < 0:
            raise ValueError("duration must be non-negative or None")
        started_at = time.time()
        timed_out = False
        codes: dict[str, int | None] = {}
        try:
            self.start()
            codes = self.wait(duration)
            if any(code is None for code in codes.values()):
                timed_out = True
                codes = self.stop()
        finally:
            if self._started and any(proc.poll() is None for proc in self._procs.values()):
                codes = self.stop()
            self._close_handles()
        return FederationResult(
            exit_codes=dict(codes),
            started_at=started_at,
            duration_s=time.time() - started_at,
            timed_out=timed_out,
            log_dir=self.log_dir,
            statuses=tuple(self.status()),
        )

    def __enter__(self) -> Federation:
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if any(proc.poll() is None for proc in self._procs.values()):
                self.stop()
        finally:
            self._close_handles()
