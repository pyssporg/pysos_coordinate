"""Endpoint addresses a federated instance offers or consumes.

An endpoint is deliberately protocol-free: it says *where* to reach a service,
not what runs on top of it. Two transports are supported for addressing: UDP
``host:port`` pairs, which the family uses for best-effort telemetry, and Unix
domain sockets, either filesystem paths or Linux abstract names (``@name``).
The package still knows nothing about the payload.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

LOOPBACK = "127.0.0.1"
_TRANSPORTS = frozenset({"udp", "unix"})


def _check_port(port: int) -> None:
    if isinstance(port, bool) or not isinstance(port, int):
        raise TypeError(f"port must be an int, got {type(port).__name__}")
    if not 1 <= port <= 65535:
        raise ValueError(f"port out of range 1..65535: {port}")


def _check_path(path: str) -> None:
    if not isinstance(path, str):
        raise TypeError(f"path must be a string, got {type(path).__name__}")
    if not path or not path.strip():
        raise ValueError("unix endpoint path must be a non-empty string")
    if path.startswith("@"):
        if len(path) == 1:
            raise ValueError("abstract unix endpoint path must name something after '@'")
        return
    if not path.startswith("/"):
        raise ValueError(f"unix endpoint path must be absolute or '@name': {path!r}")


@dataclass(frozen=True, slots=True)
class Endpoint:
    """A reachable address. Frozen so it can live in sets and dict keys.

    The first two fields stay ``host, port`` so ``Endpoint("127.0.0.1", 5510)``
    keeps working. A UDP endpoint uses ``host`` and ``port``; a Unix endpoint
    uses ``path`` and leaves ``port`` unset. ``transport`` defaults to ``"udp"``
    so a missing JSON key means the original host/port shape.
    """

    host: str = LOOPBACK
    port: int | None = None
    transport: str = "udp"
    path: str | None = None

    def __post_init__(self) -> None:
        if self.transport not in _TRANSPORTS:
            raise ValueError(
                f"endpoint transport must be one of {sorted(_TRANSPORTS)}, "
                f"got {self.transport!r}"
            )
        if self.transport == "unix":
            if self.port is not None:
                raise ValueError("unix endpoint must not declare a port")
            if self.path is None:
                raise ValueError("unix endpoint requires a path")
            _check_path(self.path)
            return
        if self.path is not None:
            raise ValueError("udp endpoint must not declare a unix path")
        if not isinstance(self.host, str) or not self.host.strip():
            raise ValueError("endpoint host must be a non-empty string")
        _check_port(self.port)  # type: ignore[arg-type]

    @classmethod
    def udp(cls, port: int, host: str = LOOPBACK) -> Endpoint:
        """UDP endpoint on *port* (loopback by default)."""
        return cls(host=host, port=port)

    @classmethod
    def unix(cls, path: str) -> Endpoint:
        """Unix domain socket at an absolute *path* or an abstract ``@name``."""
        return cls(port=None, transport="unix", path=path)

    @property
    def address(self) -> str:
        """``host:port`` for UDP, the path for a Unix socket."""
        if self.transport == "unix":
            return self.path or ""
        return f"{self.host}:{self.port}"

    def to_json(self) -> dict[str, Any]:
        if self.transport == "unix":
            return {"transport": "unix", "path": self.path}
        return {"host": self.host, "port": self.port}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Endpoint:
        if not isinstance(data, dict):
            raise TypeError("endpoint JSON must be an object")
        transport = data.get("transport", "udp")
        if transport == "unix":
            try:
                path = data["path"]
            except KeyError as exc:  # pragma: no cover - message only
                raise ValueError(f"endpoint JSON missing key {exc.args[0]!r}") from None
            return cls(transport="unix", path=path)
        try:
            host = data["host"]
            port = data["port"]
        except KeyError as exc:  # pragma: no cover - message only
            raise ValueError(f"endpoint JSON missing key {exc.args[0]!r}") from None
        return cls(host=host, port=port, transport=transport)

    def __str__(self) -> str:
        return self.address
