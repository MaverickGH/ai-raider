"""Self-serve egress scoping in AiRaiderDockerSandboxClient.

In self-serve mode (untrusted user scan) the sandbox must not reach the host and
must land on the injected per-scan ``--internal`` network. The host-gateway alias
is dropped, and starting without an injected network is refused (fail closed).
Local/trusted runs are unchanged: they keep the host-gateway alias.
"""

from __future__ import annotations

from typing import Any

import pytest

from airaider.runtime.docker_client import _apply_network_and_scope, _self_serve


def test_self_serve_flag_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIRAIDER_SELF_SERVE", raising=False)
    assert _self_serve() is False
    for on in ("1", "true", "TRUE", "yes", "on"):
        monkeypatch.setenv("AIRAIDER_SELF_SERVE", on)
        assert _self_serve() is True
    for off in ("0", "false", "no", ""):
        monkeypatch.setenv("AIRAIDER_SELF_SERVE", off)
        assert _self_serve() is False


def test_local_mode_adds_host_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIRAIDER_SELF_SERVE", raising=False)
    monkeypatch.delenv("AIRAIDER_DOCKER_SANDBOX_NETWORK", raising=False)
    kwargs: dict[str, Any] = {}
    _apply_network_and_scope(kwargs)
    assert kwargs["extra_hosts"]["host.docker.internal"] == "host-gateway"
    assert "network" not in kwargs


def test_self_serve_drops_host_gateway_and_keeps_injected_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AIRAIDER_SELF_SERVE", "1")
    monkeypatch.setenv("AIRAIDER_DOCKER_SANDBOX_NETWORK", "airaider-egress-abc123")
    kwargs: dict[str, Any] = {"ports": {"8080/tcp": ("127.0.0.1", None)}}
    _apply_network_and_scope(kwargs)
    # No path to the host.
    assert "host.docker.internal" not in kwargs.get("extra_hosts", {})
    # Lands on the injected per-scan network; published ports are dropped.
    assert kwargs["network"] == "airaider-egress-abc123"
    assert "ports" not in kwargs


def test_self_serve_without_network_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIRAIDER_SELF_SERVE", "1")
    monkeypatch.delenv("AIRAIDER_DOCKER_SANDBOX_NETWORK", raising=False)
    with pytest.raises(RuntimeError, match="unrestricted egress"):
        _apply_network_and_scope({})
