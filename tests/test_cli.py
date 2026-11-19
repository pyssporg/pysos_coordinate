from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _run(*args: object, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    return subprocess.run(
        [sys.executable, "-m", "pysos_coordinate", *(str(arg) for arg in args)],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
        timeout=60,
    )


def _manifest(tmp_path: Path, payload: dict, name: str = "federation.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _valid_payload() -> dict:
    return {
        "schema": 1,
        "name": "demo",
        "timing": "wall_clock",
        "instances": [
            {"name": "alpha", "command": [sys.executable, "-c", "print('hi')"]},
        ],
    }


def test_validate_ok(tmp_path: Path) -> None:
    result = _run("validate", _manifest(tmp_path, _valid_payload()))
    assert result.returncode == 0
    assert "ok: demo (1 instance(s)" in result.stdout


def test_validate_rejects_invalid_and_missing(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["instances"].append(dict(payload["instances"][0]))
    invalid = _run("validate", _manifest(tmp_path, payload))
    assert invalid.returncode == 1
    assert "invalid:" in invalid.stderr
    assert "duplicate instance name" in invalid.stderr

    missing = _run("validate", tmp_path / "nope.json")
    assert missing.returncode == 1
    assert "cannot read manifest" in missing.stderr

    malformed = _valid_payload()
    malformed["instances"][0]["env"] = ["not", "an", "object"]
    broken = _run("validate", _manifest(tmp_path, malformed, "broken.json"))
    assert broken.returncode == 1
    assert "env must be an object" in broken.stderr


def test_ports_prints_deterministic_allocation(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["instances"].extend(
        [
            {"name": "beta", "command": [sys.executable, "-c", "pass"]},
            {
                "name": "gamma",
                "command": [sys.executable, "-c", "pass"],
                "telemetry": [{"host": "127.0.0.1", "port": 5501}],
            },
        ]
    )
    manifest = _manifest(tmp_path, payload)
    first = _run("ports", manifest)
    second = _run("ports", manifest)
    assert first.returncode == 0
    assert first.stdout == second.stdout
    assert "alpha" in first.stdout and "gamma" in first.stdout
    # 5501 is declared by gamma, so the allocator must skip it for alpha.
    assert "127.0.0.1:5503" in first.stdout
    assert "127.0.0.1:5504" in first.stdout


def test_run_success_json(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    result = _run("run", _manifest(tmp_path, _valid_payload()), "--log-dir", logs, "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["exit_codes"] == {"alpha": 0}
    assert payload["timed_out"] is False
    assert payload["duration_s"] >= 0
    assert "hi" in (logs / "alpha.stdout.log").read_text()
    assert str(logs) in result.stderr


def test_run_reports_failures(tmp_path: Path) -> None:
    failing = _valid_payload()
    failing["instances"][0]["command"] = [sys.executable, "-c", "raise SystemExit(3)"]
    result = _run("run", _manifest(tmp_path, failing))
    assert result.returncode == 1
    assert "exit 3" in result.stdout

    slow = _valid_payload()
    slow["instances"][0]["command"] = [sys.executable, "-c", "import time; time.sleep(30)"]
    timed = _run("run", _manifest(tmp_path, slow, "slow.json"), "--duration", "0.2", "--json")
    assert timed.returncode == 1
    assert json.loads(timed.stdout)["timed_out"] is True


def test_version_and_help() -> None:
    version = _run("--version")
    assert version.returncode == 0
    assert version.stdout.strip() == "pysos-coordinate 0.2.0"
    help_text = _run("--help")
    assert help_text.returncode == 0
    for command in ("run", "validate", "ports"):
        assert command in help_text.stdout
