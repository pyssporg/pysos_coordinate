"""Timing policy for a federation.

At 0.2.0 exactly one policy exists: ``WALL_CLOCK``. Instances advance on their
own clocks and the supervisor only bounds their lifetime. Deterministic
lock-step co-simulation (a master algorithm negotiating time advances with the
instances) is an explicit non-goal of this package; it belongs to whoever owns
the federation protocol, not to the process supervisor.
"""

from __future__ import annotations

from enum import Enum


class TimingPolicy(str, Enum):
    """How a federation advances time."""

    WALL_CLOCK = "wall_clock"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value

    @classmethod
    def coerce(cls, value: object) -> TimingPolicy:
        """Accept the enum member or its JSON string form."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            try:
                return cls(value)
            except ValueError:
                pass
        raise ValueError(
            f"unsupported timing policy {value!r}; 0.2.0 supports only "
            f"{cls.WALL_CLOCK.value!r}. Lock-step co-simulation is out of scope."
        )
