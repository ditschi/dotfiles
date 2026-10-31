"""ssh-route: route order, learned home network, Tailscale and jump host."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest

from package_sets import REPO

SCRIPT = REPO / "home/core/.local/bin/ssh-route"
HOME_MAC = "76:fa:29:55:33:08"
KEY = "ssh-ed25519 AAAAhome"


def load():
    loader = importlib.machinery.SourceFileLoader("ssh_route", str(SCRIPT))
    spec = importlib.util.spec_from_loader("ssh_route", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture
def route(tmp_path, monkeypatch):
    module = load()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("MACHINE_STATE_DIR", str(tmp_path / "state"))
    calls = {"direct": [], "exec": [], "scan": 0}
    state = {"mac": HOME_MAC, "scan": {KEY}, "known": {KEY}, "reachable": True}
    monkeypatch.setattr(module, "gateway_mac", lambda: state["mac"])
    monkeypatch.setattr(module, "known_keys", lambda alias: set(state["known"]))

    def scanned(host, port):
        calls["scan"] += 1
        return set(state["scan"])

    monkeypatch.setattr(module, "scanned_keys", scanned)
    monkeypatch.setattr(module, "reachable", lambda *a, **k: state["reachable"])
    monkeypatch.setattr(
        module,
        "connect_direct",
        lambda host, port: calls["direct"].append((host, port)) or 0,
    )
    monkeypatch.setattr(
        module.os, "execvp", lambda prog, args: calls["exec"].append(args) or 0
    )
    monkeypatch.setattr(module, "on_jump_host", lambda jump: False)
    monkeypatch.setattr(
        module, "tailscale_peer_online", lambda name: (False, "tailscale not installed")
    )
    return module, state, calls, tmp_path


def cache(tmp_path: Path) -> dict:
    path = tmp_path / "cache/ssh-route/networks"
    return json.loads(path.read_text()) if path.is_file() else {}


ARGS = ["homeserver", "lan=192.168.1.4:22", "ts=homeserver:22", "jump=oracle:2223"]


def test_unknown_home_network_is_learned_and_used(route):
    module, _state, calls, tmp = route
    assert module.main(ARGS) == 0
    assert calls["direct"] == [("192.168.1.4", 22)]
    assert cache(tmp)[HOME_MAC]["state"] == "home"


def test_known_home_network_skips_keyscan(route):
    module, _state, calls, _tmp = route
    module.main(ARGS)
    module.main(ARGS)
    assert calls["scan"] == 1
    assert len(calls["direct"]) == 2


def test_foreign_network_with_same_subnet_goes_to_jump(route):
    module, state, calls, tmp = route
    state.update(mac="aa:bb:cc:dd:ee:ff", scan={"ssh-ed25519 AAAAforeign"})
    assert module.main(ARGS) == 0
    assert calls["direct"] == []
    assert calls["exec"] == [["ssh", "-W", "localhost:2223", "oracle"]]
    assert cache(tmp)["aa:bb:cc:dd:ee:ff"]["state"] == "away"


def test_recent_away_network_is_not_probed_again(route):
    module, state, calls, _tmp = route
    state.update(mac="aa:bb:cc:dd:ee:ff", scan=set())
    module.main(ARGS)
    module.main(ARGS)
    assert calls["scan"] == 1


def test_expired_away_entry_is_probed_again(route):
    module, state, calls, _tmp = route
    state.update(mac="aa:bb:cc:dd:ee:ff", scan=set())
    assert module.lan_decision("homeserver", "192.168.1.4:22", now=1000.0)[0] is False
    assert (
        module.lan_decision(
            "homeserver", "192.168.1.4:22", now=1000.0 + module.AWAY_TTL + 1
        )[0]
        is False
    )
    assert calls["scan"] == 2


def test_replaced_home_gateway_is_learned_and_reported(route):
    module, state, calls, tmp = route
    module.main(ARGS)
    state["mac"] = "11:22:33:44:55:66"
    module.main(ARGS)
    networks = cache(tmp)
    assert {mac for mac, v in networks.items() if v["state"] == "home"} == {
        HOME_MAC,
        "11:22:33:44:55:66",
    }
    events = (tmp / "state/events.jsonl").read_text()
    assert '"outcome":"home-gateway-learned"' in events
    assert HOME_MAC not in events and "11:22:33" not in events
    assert len(calls["direct"]) == 2


def test_no_known_host_key_skips_lan(route):
    module, state, calls, _tmp = route
    state["known"] = set()
    module.main(ARGS)
    assert calls["direct"] == [] and calls["exec"]


def test_tailscale_used_when_peer_online(route, monkeypatch):
    module, state, calls, _tmp = route
    state.update(mac="aa:bb:cc:dd:ee:ff", scan=set())
    monkeypatch.setattr(module, "tailscale_peer_online", lambda name: (True, ""))
    module.main(ARGS)
    assert calls["direct"] == [("homeserver", 22)]
    assert calls["exec"] == []


def test_tailscale_hanging_falls_back_to_jump(route, monkeypatch):
    module, state, calls, _tmp = route
    state.update(mac="aa:bb:cc:dd:ee:ff", scan=set())
    monkeypatch.setattr(module, "tailscale_peer_online", lambda name: (True, ""))
    state["reachable"] = False
    module.main(ARGS)
    assert calls["direct"] == []
    assert calls["exec"] == [["ssh", "-W", "localhost:2223", "oracle"]]


def test_on_jump_host_uses_local_tunnel(route, monkeypatch):
    module, state, calls, _tmp = route
    state.update(mac="aa:bb:cc:dd:ee:ff", scan=set())
    monkeypatch.setattr(module, "on_jump_host", lambda jump: True)
    module.main(ARGS)
    assert calls["direct"] == [("localhost", 2223)]
    assert calls["exec"] == []


def test_no_route_lists_reasons(route, capsys):
    module, state, _calls, _tmp = route
    state.update(mac="aa:bb:cc:dd:ee:ff", scan=set())
    assert module.main(["homeserver", "lan=192.168.1.4:22", "ts=homeserver:22"]) == 255
    err = capsys.readouterr().err
    assert "lan: not on the home network" in err
    assert "ts: tailscale not installed" in err


def test_unknown_argument_is_rejected(route):
    module, *_ = route
    with pytest.raises(SystemExit):
        module.main(["homeserver", "wifi=1"])


def test_gateway_from_proc(tmp_path):
    module = load()
    (tmp_path / "route").write_text(
        "Iface\tDestination\tGateway\tFlags\n"
        "wlan0\t0001A8C0\t00000000\t0001\n"
        "wlan0\t00000000\t0101A8C0\t0003\n"
    )
    (tmp_path / "arp").write_text(
        "IP address HW type Flags HW address Mask Device\n"
        "192.168.1.1 0x1 0x2 76:FA:29:55:33:08 * wlan0\n"
    )
    assert module.default_gateway(tmp_path) == "192.168.1.1"
    assert module.gateway_mac(tmp_path) == HOME_MAC
