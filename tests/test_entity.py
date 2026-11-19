from __future__ import annotations

import pytest

from pysos_simulate.entity import EntityRef


def test_json_roundtrip() -> None:
    ref = EntityRef("lab", "alpha", "aircraft", "secret")
    assert EntityRef.from_json(ref.to_json()) == ref
    assert ref.to_json() == {
        "site": "lab",
        "application": "alpha",
        "entity": "aircraft",
        "marking": "secret",
    }


def test_marking_is_part_of_identity() -> None:
    plain = EntityRef("lab", "alpha", "aircraft")
    secret = EntityRef("lab", "alpha", "aircraft", "secret")
    assert plain != secret
    assert plain.marking == ""
    assert len({plain, secret, EntityRef("lab", "alpha", "aircraft")}) == 2


def test_rejects_blank_site() -> None:
    with pytest.raises(ValueError, match="site"):
        EntityRef("", "alpha", "aircraft")
