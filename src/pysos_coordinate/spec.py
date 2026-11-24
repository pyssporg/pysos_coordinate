"""Manifest types: one instance, and the federation that supervises many.

This module owns the execution-manifest schema. Its normative definition,
including compatibility rules, is ``docs/breakdown/02-architecture/manifest.md``.

A manifest is plain data. ``FederationSpec.validate`` is the single gate that
decides whether a federation may be started; the supervisor calls it and the
CLI calls it, so an invalid manifest fails the same way everywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .endpoint import Endpoint
from .entity import EntityRef
from .timing import TimingPolicy

SCHEMA_VERSION = 2
SUPPORTED_SCHEMAS = (1, SCHEMA_VERSION)


class SpecError(ValueError):
    """A manifest is structurally valid JSON but not a valid federation."""


def _as_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise SpecError(f"{field_name} must be a string, got {type(value).__name__}")
    if not value.strip():
        raise SpecError(f"{field_name} must be a non-empty string")
    return value


@dataclass
class InstanceSpec:
    """One independently launched simulation process.

    ``command`` is argv, never a shell string: the supervisor passes it to
    ``subprocess.Popen`` with ``shell=False``. ``env`` is layered on top of the
    supervisor's own environment (so ``PATH`` still resolves) and wins on
    conflict.
    """

    name: str
    command: list[str]
    cwd: Path | None = None
    env: dict[str, str] = field(default_factory=dict)
    entities: list[EntityRef] = field(default_factory=list)
    telemetry: list[Endpoint] = field(default_factory=list)
    control: list[Endpoint] = field(default_factory=list)
    startup_timeout: float = 30.0

    def __post_init__(self) -> None:
        if isinstance(self.cwd, str):
            self.cwd = Path(self.cwd)
        self.entities = list(self.entities)
        self.telemetry = list(self.telemetry)
        self.control = list(self.control)
        self.command = list(self.command)
        self.env = dict(self.env)

    def validate(self) -> None:
        _as_text(self.name, "instance name")
        if not self.command:
            raise SpecError(f"instance {self.name!r}: command must not be empty")
        for arg in self.command:
            if not isinstance(arg, str):
                raise SpecError(
                    f"instance {self.name!r}: command entries must be strings, "
                    f"got {type(arg).__name__}"
                )
        if not self.command[0].strip():
            raise SpecError(f"instance {self.name!r}: command[0] must be non-empty")
        if self.cwd is not None and not isinstance(self.cwd, Path):
            raise SpecError(f"instance {self.name!r}: cwd must be a Path or null")
        for key, value in self.env.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise SpecError(f"instance {self.name!r}: env must map strings to strings")
        if isinstance(self.startup_timeout, bool) or not isinstance(
            self.startup_timeout, (int, float)
        ):
            raise SpecError(f"instance {self.name!r}: startup_timeout must be a number")
        if self.startup_timeout <= 0:
            raise SpecError(f"instance {self.name!r}: startup_timeout must be positive")
        seen_entities: set[EntityRef] = set()
        for entity in self.entities:
            if not isinstance(entity, EntityRef):
                raise SpecError(f"instance {self.name!r}: entities must be EntityRef values")
            if entity in seen_entities:
                raise SpecError(f"instance {self.name!r}: duplicate entity {entity}")
            seen_entities.add(entity)
        for kind, endpoints in (("telemetry", self.telemetry), ("control", self.control)):
            for endpoint in endpoints:
                if not isinstance(endpoint, Endpoint):
                    raise SpecError(
                        f"instance {self.name!r}: {kind} entries must be Endpoint values"
                    )

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "command": list(self.command),
            "cwd": None if self.cwd is None else str(self.cwd),
            "env": dict(self.env),
            "entities": [entity.to_json() for entity in self.entities],
            "telemetry": [endpoint.to_json() for endpoint in self.telemetry],
            "control": [endpoint.to_json() for endpoint in self.control],
            "startup_timeout": self.startup_timeout,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> InstanceSpec:
        if not isinstance(data, dict):
            raise SpecError("instance JSON must be an object")
        try:
            name = data["name"]
            command = data["command"]
        except KeyError as exc:
            raise SpecError(f"instance JSON missing key {exc.args[0]!r}") from None
        if not isinstance(command, list):
            raise SpecError(f"instance {name!r}: command must be a list of strings")
        cwd = data.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise SpecError(f"instance {name!r}: cwd must be a string or null")
        env = data.get("env") or {}
        if not isinstance(env, dict):
            raise SpecError(f"instance {name!r}: env must be an object")
        lists: dict[str, list] = {}
        for key in ("entities", "telemetry", "control"):
            value = data.get(key) or []
            if not isinstance(value, list):
                raise SpecError(f"instance {name!r}: {key} must be a list")
            lists[key] = value
        return cls(
            name=name,
            command=list(command),
            cwd=None if cwd is None else Path(cwd),
            env=dict(env),
            entities=[EntityRef.from_json(item) for item in lists["entities"]],
            telemetry=[Endpoint.from_json(item) for item in lists["telemetry"]],
            control=[Endpoint.from_json(item) for item in lists["control"]],
            startup_timeout=data.get("startup_timeout", 30.0),
        )


def _merge_endpoint(
    seen: dict[Endpoint, str], endpoint: Endpoint, owner: str, problems: list[str]
) -> None:
    other = seen.get(endpoint)
    if other is None:
        seen[endpoint] = owner
    else:
        problems.append(f"endpoint {endpoint} is declared by both {other} and {owner}")


def _merge_unix_path(
    seen: dict[str, str], path: str, owner: str, problems: list[str]
) -> None:
    other = seen.get(path)
    if other is None:
        seen[path] = owner
    elif other != owner:
        problems.append(
            f"duplicate unix path {path!r} is declared by both {other} and {owner}"
        )


def _uses_unix_endpoints(spec: FederationSpec) -> bool:
    return any(
        isinstance(endpoint, Endpoint) and endpoint.transport == "unix"
        for instance in spec.instances
        if isinstance(instance, InstanceSpec)
        for endpoint in (*instance.telemetry, *instance.control)
    )


@dataclass
class FederationSpec:
    """A named set of instances supervised together."""

    name: str
    instances: list[InstanceSpec] = field(default_factory=list)
    schema: int = SCHEMA_VERSION
    timing: TimingPolicy = TimingPolicy.WALL_CLOCK

    def __post_init__(self) -> None:
        self.instances = list(self.instances)
        if isinstance(self.timing, str):
            try:
                self.timing = TimingPolicy.coerce(self.timing)
            except ValueError as exc:
                raise SpecError(str(exc)) from None

    def validate(self) -> FederationSpec:
        """Raise ``SpecError`` on the first problem; return ``self`` otherwise."""
        _as_text(self.name, "federation name")
        if isinstance(self.schema, bool) or not isinstance(self.schema, int):
            raise SpecError(f"schema must be an int, got {type(self.schema).__name__}")
        if self.schema not in SUPPORTED_SCHEMAS:
            supported = " and ".join(str(value) for value in SUPPORTED_SCHEMAS)
            raise SpecError(
                f"unsupported manifest schema {self.schema}; this release reads schema "
                f"{supported}"
            )
        if self.schema == 1 and _uses_unix_endpoints(self):
            raise SpecError("unix endpoints require schema 2")
        try:
            self.timing = TimingPolicy.coerce(self.timing)
        except ValueError as exc:
            raise SpecError(str(exc)) from None
        if self.timing is not TimingPolicy.WALL_CLOCK:
            raise SpecError(
                "timing policy must be 'wall_clock' at 0.4.0; deterministic lock-step "
                "co-simulation is an explicit non-goal of pysos_coordinate"
            )
        if not self.instances:
            raise SpecError("federation must declare at least one instance")

        names: set[str] = set()
        endpoints: dict[Endpoint, str] = {}
        unix_paths: dict[str, str] = {}
        problems: list[str] = []
        for instance in self.instances:
            if not isinstance(instance, InstanceSpec):
                raise SpecError("instances must be InstanceSpec values")
            instance.validate()
            if instance.name in names:
                problems.append(f"duplicate instance name {instance.name!r}")
            names.add(instance.name)
            seen_local: set[Endpoint] = set()
            for kind, declared in (
                ("telemetry", instance.telemetry),
                ("control", instance.control),
            ):
                owner = f"{instance.name}.{kind}"
                for endpoint in declared:
                    if endpoint in seen_local:
                        problems.append(
                            f"instance {instance.name!r}: duplicate endpoint {endpoint}"
                        )
                    seen_local.add(endpoint)
                    _merge_endpoint(endpoints, endpoint, instance.name, problems)
                    if endpoint.transport == "unix" and endpoint.path is not None:
                        _merge_unix_path(unix_paths, endpoint.path, owner, problems)
        if problems:
            raise SpecError("; ".join(problems))
        return self

    def to_json(self) -> dict[str, Any]:
        schema = 2 if _uses_unix_endpoints(self) else self.schema
        return {
            "schema": schema,
            "name": self.name,
            "timing": self.timing.value,
            "instances": [instance.to_json() for instance in self.instances],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> FederationSpec:
        if not isinstance(data, dict):
            raise SpecError("federation JSON must be an object")
        try:
            name = data["name"]
            instances = data["instances"]
        except KeyError as exc:
            raise SpecError(f"federation JSON missing key {exc.args[0]!r}") from None
        if not isinstance(instances, list):
            raise SpecError("instances must be a list")
        spec = cls(
            name=name,
            instances=[InstanceSpec.from_json(item) for item in instances],
            schema=data.get("schema", SCHEMA_VERSION),
            timing=data.get("timing", TimingPolicy.WALL_CLOCK.value),
        )
        return spec.validate()
