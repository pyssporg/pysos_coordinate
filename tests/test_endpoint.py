from __future__ import annotations

import pytest

from pysos_coordinate.endpoint import Endpoint


def test_json_roundtrip() -> None:
    endpoint = Endpoint("10.0.0.5", 6001)
    assert Endpoint.from_json(endpoint.to_json()) == endpoint
    assert endpoint.to_json() == {"host": "10.0.0.5", "port": 6001}


def test_udp_defaults_to_loopback() -> None:
    assert Endpoint.udp(5501) == Endpoint("127.0.0.1", 5501)
    assert Endpoint.udp(5501, host="0.0.0.0") == Endpoint("0.0.0.0", 5501)


def test_endpoints_dedupe_as_set() -> None:
    assert len({Endpoint.udp(5501), Endpoint.udp(5501)}) == 1
    assert len({Endpoint.udp(5501), Endpoint.udp(5503)}) == 2


def test_rejects_bad_port() -> None:
    for port in (0, -1, 65536):
        with pytest.raises(ValueError, match="port out of range"):
            Endpoint("127.0.0.1", port)


def test_rejects_blank_host() -> None:
    for host in ("", "   "):
        with pytest.raises(ValueError, match="host"):
            Endpoint(host, 5501)
