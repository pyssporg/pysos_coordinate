"""Local, duplicate-free reference to a simulated entity.

At 0.1.0 this type is intentionally local to ``pysos_simulate``. It does not
import ``pysos_interop``. The two definitions agree *by field name*:
``site``, ``application``, ``entity``, and ``marking``. A future release may
consolidate them once ``pysos_interop`` can be depended on; until then the
duplication keeps this package installable with the standard library alone.

Used as a set/dict key, an ``EntityRef`` is duplicate-free by construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _check_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"entity {field_name} must be a string, got {type(value).__name__}")
    return value


@dataclass(frozen=True, slots=True)
class EntityRef:
    """Reference to one entity inside one application at one site.

    ``marking`` is the security marking attached to the reference. It is part
    of the identity on purpose: the same entity under two markings is two
    distinct references.
    """

    site: str
    application: str
    entity: str
    marking: str = ""

    def __post_init__(self) -> None:
        for name in ("site", "application", "entity"):
            if not _check_text(getattr(self, name), name).strip():
                raise ValueError(f"entity {name} must be a non-empty string")
        _check_text(self.marking, "marking")

    def to_json(self) -> dict[str, str]:
        return {
            "site": self.site,
            "application": self.application,
            "entity": self.entity,
            "marking": self.marking,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> EntityRef:
        if not isinstance(data, dict):
            raise TypeError("entity JSON must be an object")
        try:
            return cls(
                site=data["site"],
                application=data["application"],
                entity=data["entity"],
                marking=data.get("marking", ""),
            )
        except KeyError as exc:
            raise ValueError(f"entity JSON missing key {exc.args[0]!r}") from None

    def __str__(self) -> str:
        base = f"{self.site}/{self.application}/{self.entity}"
        return f"{base}#{self.marking}" if self.marking else base
