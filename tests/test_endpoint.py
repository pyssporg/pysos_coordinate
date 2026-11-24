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


def test_unix_construction_and_address() -> None:
    assert Endpoint.unix("/tmp/alpha.sock").address == "/tmp/alpha.sock"
    assert Endpoint.unix("@alpha").address == "@alpha"
    assert Endpoint.unix("/tmp/alpha.sock") == Endpoint(
        transport="unix", path="/tmp/alpha.sock"
    )
    assert str(Endpoint.unix("@alpha")) == "@alpha"
    assert len({Endpoint.unix("@alpha"), Endpoint.unix("@alpha")}) == 1


def test_unix_json_roundtrip() -> None:
    endpoint = Endpoint.unix("@alpha")
    assert endpoint.to_json() == {"transport": "unix", "path": "@alpha"}
    assert Endpoint.from_json(endpoint.to_json()) == endpoint
    assert Endpoint.from_json({"path": "/tmp/a.sock", "transport": "unix"}) == Endpoint.unix(
        "/tmp/a.sock"
    )


def test_udp_json_has_no_new_keys_and_missing_transport_is_udp() -> None:
    endpoint = Endpoint.udp(5501)
    assert endpoint.to_json() == {"host": "127.0.0.1", "port": 5501}
    assert Endpoint.from_json({"host": "127.0.0.1", "port": 5501}) == endpoint
    assert Endpoint.from_json({"host": "127.0.0.1", "port": 5501}) == Endpoint("127.0.0.1", 5501)


def test_rejects_invalid_endpoint_combinations() -> None:
    with pytest.raises(ValueError, match="must not declare a port"):
        Endpoint(transport="unix", port=5501, path="@alpha")
    with pytest.raises(ValueError, match="must not declare a unix path"):
        Endpoint("127.0.0.1", 5501, path="/tmp/a.sock")
    with pytest.raises(ValueError, match="requires a path"):
        Endpoint(transport="unix")
    with pytest.raises(ValueError, match="non-empty"):
        Endpoint.unix("")
    with pytest.raises(ValueError, match="absolute or '@name'"):
        Endpoint.unix("relative.sock")
    with pytest.raises(ValueError, match="after '@'"):
        Endpoint.unix("@")
    with pytest.raises(ValueError, match="transport"):
        Endpoint("127.0.0.1", 5501, transport="tcp")
