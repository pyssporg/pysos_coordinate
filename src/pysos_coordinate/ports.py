"""Deterministic, collision-aware port assignment.

The allocator hands each instance a telemetry port and a control port from a
contiguous band::

    base + index * stride      telemetry
    base + index * stride + 1  control

``index`` is the order in which instances are first allocated, so a given
manifest and call order always produce the same map. ``reserve`` marks ports
that are already spoken for (for example the ports a manifest declares) so the
allocator never hands them out, and ``conflicts`` reports overlaps against a
whole manifest before anything is launched.
"""

from __future__ import annotations

import hashlib
import re

from .endpoint import LOOPBACK, Endpoint
from .spec import FederationSpec, InstanceSpec

_UNIX_UNSAFE = re.compile(r"[^a-z0-9-]+")
_UNIX_DASHES = re.compile(r"-{2,}")
_MAX_ABSTRACT_BYTES = 80
_MAX_ATTEMPTS = 10_000


class PortAllocator:
    """Allocate ``(telemetry, control)`` endpoint pairs from a base/stride band."""

    def __init__(self, base: int = 5501, stride: int = 2) -> None:
        if isinstance(base, bool) or not isinstance(base, int):
            raise TypeError("base must be an int")
        if isinstance(stride, bool) or not isinstance(stride, int):
            raise TypeError("stride must be an int")
        if not 1 <= base <= 65534:
            raise ValueError(f"base out of usable range 1..65534: {base}")
        if stride < 2:
            raise ValueError(f"stride must be at least 2 to fit a control port: {stride}")
        self.base = base
        self.stride = stride
        self._reserved: set[Endpoint] = set()
        self._owned_by_spec: dict[int, set[Endpoint]] = {}
        self._assigned: dict[str, tuple[Endpoint, Endpoint]] = {}
        self._cursor = 0

    @property
    def reserved(self) -> frozenset[Endpoint]:
        return frozenset(self._reserved)

    @property
    def allocations(self) -> dict[str, tuple[Endpoint, Endpoint]]:
        return dict(self._assigned)

    def reserve(self, endpoint: Endpoint) -> None:
        """Mark *endpoint* as taken; raises if it was already reserved."""
        if endpoint in self._reserved:
            raise ValueError(f"endpoint already reserved: {endpoint}")
        self._reserved.add(endpoint)

    def reserve_spec(self, spec: FederationSpec) -> None:
        """Reserve every endpoint a manifest already declares.

        Ports newly taken here are remembered per manifest, so ``conflicts`` on
        the same manifest does not report them as external collisions.
        """
        owned = self._owned_by_spec.setdefault(id(spec), set())
        for instance in spec.instances:
            for endpoint in (*instance.telemetry, *instance.control):
                if endpoint not in self._reserved:
                    self._reserved.add(endpoint)
                    owned.add(endpoint)

    def allocate(self, instance: InstanceSpec | str) -> tuple[Endpoint, Endpoint]:
        """Return ``(telemetry, control)`` for *instance*; idempotent per name."""
        name = instance.name if isinstance(instance, InstanceSpec) else str(instance)
        if not name:
            raise ValueError("instance name must be non-empty")
        cached = self._assigned.get(name)
        if cached is not None:
            return cached
        while True:
            telemetry_port = self.base + self._cursor * self.stride
            control_port = telemetry_port + 1
            if control_port > 65535:
                raise OverflowError(
                    f"port band exhausted at instance {name!r} (base={self.base}, "
                    f"stride={self.stride})"
                )
            self._cursor += 1
            telemetry = Endpoint(LOOPBACK, telemetry_port)
            control = Endpoint(LOOPBACK, control_port)
            if telemetry in self._reserved or control in self._reserved:
                continue
            self._assigned[name] = (telemetry, control)
            return telemetry, control

    def conflicts(self, spec: FederationSpec) -> list[str]:
        """Report endpoints in *spec* that collide with each other or with others.

        Ports reserved *by this spec* via ``reserve_spec`` are not conflicts;
        reservations made for anything else still are.
        """
        problems: list[str] = []
        owned = self._owned_by_spec.get(id(spec), set())
        seen: dict[Endpoint, str] = {}
        for instance in spec.instances:
            for kind, endpoints in (
                ("telemetry", instance.telemetry),
                ("control", instance.control),
            ):
                for endpoint in endpoints:
                    owner = f"{instance.name}.{kind}"
                    if endpoint in self._reserved and endpoint not in owned:
                        problems.append(f"{owner} uses reserved endpoint {endpoint}")
                    other = seen.get(endpoint)
                    if other is not None and other != owner:
                        problems.append(f"{owner} and {other} share endpoint {endpoint}")
                    seen.setdefault(endpoint, owner)
        return problems


def _sanitize_unix_name(name: str) -> str:
    text = _UNIX_UNSAFE.sub("-", name.strip().lower())
    text = _UNIX_DASHES.sub("-", text).strip("-")
    return text or "instance"


class UnixAllocator:
    """Allocate deterministic abstract Unix socket paths per instance name.

    The default address is ``@<prefix>-<sanitized-name>``. Sanitizing lowercases
    the name, maps every character outside ``[a-z0-9-]`` to ``-``, and collapses
    runs, so the same name always yields the same path. Reserved paths are
    skipped with a numeric suffix, and the whole abstract name is capped well
    under the 108-byte ``sun_path`` limit.
    """

    def __init__(self, prefix: str = "pysos") -> None:
        if not isinstance(prefix, str) or not prefix.strip():
            raise ValueError("prefix must be a non-empty string")
        self.prefix = _sanitize_unix_name(prefix)
        self._reserved: set[Endpoint] = set()
        self._reserved_paths: set[str] = set()
        self._assigned: dict[str, Endpoint] = {}
        self._path_owner: dict[str, str] = {}

    @property
    def reserved(self) -> frozenset[Endpoint]:
        return frozenset(self._reserved)

    @property
    def allocations(self) -> dict[str, Endpoint]:
        return dict(self._assigned)

    def reserve(self, endpoint: Endpoint) -> None:
        """Mark a Unix *endpoint* as taken; raises if its path is already reserved."""
        if not isinstance(endpoint, Endpoint):
            raise TypeError("endpoint must be an Endpoint")
        if endpoint.transport != "unix":
            raise ValueError(f"UnixAllocator reserves unix endpoints only: {endpoint}")
        if endpoint in self._reserved or endpoint.path in self._reserved_paths:
            raise ValueError(f"endpoint already reserved: {endpoint}")
        self._reserved.add(endpoint)
        self._reserved_paths.add(endpoint.path)  # type: ignore[arg-type]

    def reserve_spec(self, spec: FederationSpec) -> None:
        """Reserve every Unix endpoint a manifest already declares."""
        for instance in spec.instances:
            for endpoint in (*instance.telemetry, *instance.control):
                if endpoint.transport != "unix":
                    continue
                if endpoint in self._reserved or endpoint.path in self._reserved_paths:
                    continue
                self._reserved.add(endpoint)
                self._reserved_paths.add(endpoint.path)  # type: ignore[arg-type]

    def allocate(self, instance: InstanceSpec | str) -> Endpoint:
        """Return the abstract Unix endpoint for *instance*; idempotent per name."""
        name = instance.name if isinstance(instance, InstanceSpec) else str(instance)
        if not name:
            raise ValueError("instance name must be non-empty")
        cached = self._assigned.get(name)
        if cached is not None:
            return cached
        for suffix in range(1, _MAX_ATTEMPTS + 1):
            path = self._abstract(name, suffix)
            owner = self._path_owner.get(path)
            if path in self._reserved_paths or (owner is not None and owner != name):
                continue
            endpoint = Endpoint.unix(path)
            self._assigned[name] = endpoint
            self._path_owner[path] = name
            return endpoint
        raise OverflowError(
            f"unix name space exhausted at instance {name!r} (prefix={self.prefix!r})"
        )

    def _abstract(self, name: str, suffix: int) -> str:
        safe = _sanitize_unix_name(name)
        if suffix != 1:
            safe = f"{safe}-{suffix}"
        budget = _MAX_ABSTRACT_BYTES - len(self.prefix) - 2
        if len(safe) > budget:
            digest = hashlib.sha1(f"{name}:{suffix}".encode()).hexdigest()[:8]
            keep = max(budget - len(digest) - 1, 1)
            safe = f"{safe[:keep].rstrip('-')}-{digest}"
        return f"@{self.prefix}-{safe}"
