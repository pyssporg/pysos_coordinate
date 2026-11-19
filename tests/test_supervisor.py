from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from pysos_coordinate.spec import FederationSpec, InstanceSpec
from pysos_coordinate.supervisor import (
    Federation,
    InstanceStatus,
    LaunchError,
)


def _child(code: str, name: str = "alpha", **kwargs) -> InstanceSpec:
    return InstanceSpec(name=name, command=[sys.executable, "-c", code], **kwargs)


def _federation(*instances: InstanceSpec, log_dir: Path | None = None) -> Federation:
    return Federation(FederationSpec("demo", list(instances)), log_dir=log_dir)


def test_start_status_and_wait() -> None:
    federation = _federation(_child("import time; time.sleep(0.05)"))
    assert federation.status()[0].pid is None
    federation.start()
    status = federation.status()[0]
    assert isinstance(status, InstanceStatus)
    assert status.name == "alpha"
    assert status.pid and status.pid > 0
    assert status.started_at is not None
    assert status.running is True
    assert status.exit_code is None
    assert federation.wait(timeout=5) == {"alpha": 0}
    assert federation.status()[0].running is False


def test_reports_nonzero_exit() -> None:
    federation = _federation(_child("raise SystemExit(3)"))
    result = federation.run()
    assert result.exit_codes == {"alpha": 3}
    assert result.timed_out is False
    assert result.ok is False


def test_stop_is_graceful_when_child_handles_sigterm() -> None:
    code = (
        "import signal, sys, time\n"
        "def handle(*_):\n"
        "    print('term', flush=True)\n"
        "    raise SystemExit(0)\n"
        "signal.signal(signal.SIGTERM, handle)\n"
        "time.sleep(30)\n"
    )
    federation = _federation(_child(code))
    federation.start()
    time.sleep(0.2)
    codes = federation.stop(grace=5.0)
    assert codes == {"alpha": 0}
    assert "term" in federation.logs()["alpha"]["stdout"].read_text()


def test_stop_kills_a_child_that_ignores_sigterm() -> None:
    code = "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)"
    federation = _federation(_child(code))
    federation.start()
    time.sleep(0.2)
    codes = federation.stop(grace=0.2)
    assert codes["alpha"] == -9


def test_run_bounds_duration_and_reports_timeout() -> None:
    federation = _federation(_child("import time; time.sleep(30)"))
    result = federation.run(duration=0.2)
    assert result.timed_out is True
    assert result.duration_s < 5
    assert result.exit_codes["alpha"] is not None
    assert result.ok is False


def test_run_finishes_early_without_timeout() -> None:
    federation = _federation(_child("print('done')"))
    result = federation.run(duration=30)
    assert result.timed_out is False
    assert result.exit_codes == {"alpha": 0}
    assert result.ok is True


def test_captures_logs_in_caller_directory(tmp_path: Path) -> None:
    code = "import sys; print('out'); print('err', file=sys.stderr)"
    federation = _federation(_child(code), log_dir=tmp_path / "logs")
    result = federation.run()
    assert result.log_dir == tmp_path / "logs"
    logs = federation.logs()
    assert "out" in logs["alpha"]["stdout"].read_text()
    assert "err" in logs["alpha"]["stderr"].read_text()


def test_applies_cwd_and_env(tmp_path: Path) -> None:
    code = (
        "import os; print(os.getcwd()); print(os.environ['PYSOS_TEST']); "
        "print(os.environ['PATH'] != '')"
    )
    federation = _federation(
        _child(code, cwd=tmp_path, env={"PYSOS_TEST": "yes"}),
    )
    federation.run()
    stdout = federation.logs()["alpha"]["stdout"].read_text().splitlines()
    assert stdout[0] == str(tmp_path)
    assert stdout[1] == "yes"
    assert stdout[2] == "True"


def test_missing_executable_raises_launch_error(tmp_path: Path) -> None:
    federation = _federation(
        InstanceSpec("alpha", [str(tmp_path / "does-not-exist")]),
        log_dir=tmp_path / "logs",
    )
    with pytest.raises(LaunchError, match="failed to launch"):
        federation.start()


def test_wait_timeout_returns_running_instances() -> None:
    federation = _federation(_child("import time; time.sleep(30)"))
    federation.start()
    try:
        assert federation.wait(timeout=0.1) == {"alpha": None}
    finally:
        assert federation.stop(grace=0.5)["alpha"] == -15
