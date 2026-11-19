"""Network endpoints a federated instance offers or consumes.

An endpoint is deliberately protocol-free: it says *where* to reach a service,
not what runs on top of it. UDP is the only convenience offered at 0.2.0
because it is the transport the family uses for best-effort telemetry; the
package still knows nothing about the payload.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

LOOPBACK = "127.0.0.1"


def _check_port(port: int) -> None:
    if isinstance(port, bool) or not isinstance(port, int):
        raise TypeError(f"port must be an int, got {type(port).__name__}")
    if not 1 <= port <= 65535:
        raise ValueError(f"port out of range 1..65535: {port}")


@dataclass(frozen=True, slots=True)
class Endpoint:
    """A host/port pair. Frozen so it can live in sets and dict keys."""

    host: str
    port: int

    def __post_init__(self) -> None:
        if not isinstance(self.host, str) or not self.host.strip():
            raise ValueError("endpoint host must be a non-empty string")
        _check_port(self.port)

    @classmethod
    def udp(cls, port: int, host: str = LOOPBACK) -> Endpoint:
        """Loopback UDP endpoint on *port*."""
        return cls(host=host, port=port)

    def to_json(self) -> dict[str, Any]:
        return {"host": self.host, "port": self.port}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Endpoint:
        if not isinstance(data, dict):
            raise TypeError("endpoint JSON must be an object")
        try:
            host = data["host"]
            port = data["port"]
        except KeyError as exc:  # pragma: no cover - message only
            raise ValueError(f"endpoint JSON missing key {exc.args[0]!r}") from None
        return cls(host=host, port=port)

    def __str__(self) -> str:
        return f"{self.host}:{self.port}"
