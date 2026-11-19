"""Command line entry point: ``pysos-simulate {run,validate,ports}``."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import __version__
from .ports import PortAllocator
from .spec import FederationSpec, SpecError
from .supervisor import Federation
from .timing import TimingPolicy


def _load_manifest(path: str) -> FederationSpec:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise SpecError(f"cannot read manifest {path!r}: {exc.strerror}") from None
    except json.JSONDecodeError as exc:
        raise SpecError(f"manifest {path!r} is not valid JSON: {exc}") from None
    return FederationSpec.from_json(data)


def _print_spec(spec: FederationSpec) -> None:
    print(f"federation: {spec.name}")
    print(f"schema: {spec.schema}  timing: {spec.timing.value}  instances: {len(spec.instances)}")


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        spec = _load_manifest(args.manifest)
    except SpecError as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return 1
    print(f"ok: {spec.name} ({len(spec.instances)} instance(s), schema {spec.schema})")
    return 0


def _cmd_ports(args: argparse.Namespace) -> int:
    allocator = PortAllocator(base=args.base, stride=args.stride)
    if args.manifest:
        try:
            spec = _load_manifest(args.manifest)
            allocator.reserve_spec(spec)
            conflicts = allocator.conflicts(spec)
            rows = []
            for instance in spec.instances:
                telemetry, control = allocator.allocate(instance)
                rows.append(
                    {
                        "name": instance.name,
                        "telemetry": telemetry.to_json(),
                        "control": control.to_json(),
                    }
                )
        except SpecError as exc:
            print(f"invalid: {exc}", file=sys.stderr)
            return 1
    else:
        conflicts = []
        rows = []
        for index in (0, 1):
            name = f"instance-{index}"
            telemetry, control = allocator.allocate(name)
            rows.append(
                {
                    "name": name,
                    "telemetry": telemetry.to_json(),
                    "control": control.to_json(),
                }
            )
    if args.json:
        print(json.dumps({"base": allocator.base, "stride": allocator.stride,
                          "allocations": rows, "conflicts": conflicts}, indent=2))
    else:
        print(f"{'instance':<20} {'telemetry':<22} control")
        for row in rows:
            telemetry = f"{row['telemetry']['host']}:{row['telemetry']['port']}"
            control = f"{row['control']['host']}:{row['control']['port']}"
            print(f"{row['name']:<20} {telemetry:<22} {control}")
        for problem in conflicts:
            print(f"collision: {problem}", file=sys.stderr)
    return 1 if conflicts else 0


def _cmd_run(args: argparse.Namespace) -> int:
    try:
        spec = _load_manifest(args.manifest)
    except SpecError as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return 1
    federation = Federation(spec, log_dir=args.log_dir)
    result = federation.run(duration=args.duration)
    if args.json:
        payload: dict[str, Any] = result.to_json()
        print(json.dumps(payload, indent=2))
    else:
        _print_spec(spec)
        for status in result.statuses:
            state = "running" if status.running else f"exit {status.exit_code}"
            print(f"  {status.name:<20} pid={status.pid} {state}")
        print(f"duration: {result.duration_s:.3f}s  timed_out: {result.timed_out}")
    if result.log_dir is not None:
        print(f"logs: {result.log_dir}", file=sys.stderr)
    return 0 if result.ok and not result.timed_out else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pysos-simulate",
        description="Set up and supervise a federation of simulation instances.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="start a federation, bound it, and stop it")
    run.add_argument("manifest", help="path to a federation manifest JSON file")
    run.add_argument("--duration", type=float, default=None, metavar="S",
                     help="stop after S seconds (default: until every instance exits)")
    run.add_argument("--log-dir", type=Path, default=None,
                     help="capture stdout/stderr here (default: a temporary directory)")
    run.add_argument("--json", action="store_true", help="print the result as JSON")
    run.set_defaults(func=_cmd_run)

    validate = sub.add_parser("validate", help="check a manifest without launching anything")
    validate.add_argument("manifest")
    validate.set_defaults(func=_cmd_validate)

    ports = sub.add_parser("ports", help="print the deterministic port allocation")
    ports.add_argument("manifest", nargs="?", default=None,
                      help="reserve this manifest's declared endpoints first")
    ports.add_argument("--base", type=int, default=5501)
    ports.add_argument("--stride", type=int, default=2)
    ports.add_argument("--json", action="store_true")
    ports.set_defaults(func=_cmd_ports)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (SpecError, ValueError, OverflowError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


__all__ = ["build_parser", "main", "TimingPolicy"]
