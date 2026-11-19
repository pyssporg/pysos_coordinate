"""Allow ``python -m pysos_coordinate`` for environments without the script."""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
