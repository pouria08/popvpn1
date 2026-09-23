from __future__ import annotations

import base64
import json
from pathlib import Path

from popvpn.pipeline import Options, Pipeline, run
from popvpn.probe import ProbeSettings, probe_configs
from popvpn.protocols import parse_uri

ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_CONFIG = ROOT / "config.yaml"

VLESS = (
    "vless://a1b2c3d4-e5f6-4789-abcd-ef0123456789@8.8.8.8:443"
    "?security=none&type=tcp#quality-test"
)


def test_probe_cache_is_mode_and_ttl_aware(tmp_path, monkeypatch):
    """A TLS/expired cache result can never stand in for a fresh TCP verdict."""

    calls: list[tuple[str, bool]] = []

    def fake_probe(endpoint: str, timeout: float, use_tls: bool, sni: str):
        calls.append((endpoint, use_tls))
        return True, 17

    monkeypatch.setattr("popvpn.probe._probe_endpoint", fake_probe)
    cache_path = tmp_path / "probe.json"

    tcp_config = parse_uri(VLESS)
    first = probe_configs([tcp_config], ProbeSettings(mode="tcp", state_file=str(cache_path)))
    assert first["endpoints_probed"] == 1
    assert first["endpoints_cached"] == 0
    assert tcp_config.verified is True

    second_config = parse_uri(VLESS)
    second = probe_configs([second_config], ProbeSettings(mode="tcp", state_file=str(cache_path)))
    assert second["endpoints_probed"] == 0
    assert second["endpoints_cached"] == 1

    # The stored verdict is TCP-specific. A TLS request must run again.
    tls_config = parse_uri(VLESS)
    tls = probe_configs([tls_config], ProbeSettings(mode="tls", state_file=str(cache_path)))
    assert tls["endpoints_probed"] == 1
    assert tls["endpoints_cached"] == 0

    data = json.loads(cache_path.read_text(encoding="utf-8"))
    data["endpoints"]["8.8.8.8:443"]["at"] = 0
    data["endpoints"]["8.8.8.8:443"]["mode"] = "tcp"
    cache_path.write_text(json.dumps(data), encoding="utf-8")
    expired = probe_configs([parse_uri(VLESS)], ProbeSettings(mode="tcp", state_file=str(cache_path)))
    assert expired["endpoints_probed"] == 1
    assert expired["endpoints_cached"] == 0
    assert len(calls) == 3


def test_probe_cap_leaves_config_explicitly_unverified(tmp_path, monkeypatch):
    monkeypatch.setattr("popvpn.probe._probe_endpoint", lambda *_args: (True, 1))
    cfg = parse_uri(VLESS)
    summary = probe_configs(
        [cfg], ProbeSettings(mode="tcp", max_endpoints=0, state_file=str(tmp_path / "probe.json"))
    )
    assert summary["endpoints_unprobed"] == 1
    assert summary["configs_unprobed"] == 1
    assert cfg.verified is None


def test_production_policy_publishes_only_tcp_verified_configs(workspace, tmp_path, monkeypatch):
    """A failed TCP verdict is excluded from every public output in strict mode."""

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "source.txt").write_text(VLESS + "\n", encoding="utf-8")

    def dead_probe(configs, settings, **_kwargs):
        for cfg in configs:
            cfg.verified = False
            cfg.latency_ms = 0
        return {
            "mode": "tcp",
            "endpoints_total": 1,
            "endpoints_probed": 1,
            "endpoints_cached": 0,
            "endpoints_unprobed": 0,
            "alive": 0,
            "dead": 1,
            "configs_alive": 0,
            "configs_dead": 1,
            "configs_unprobed": 0,
            "elapsed_ms": 1,
            "avg_latency_ms": 0,
        }

    monkeypatch.setattr("popvpn.pipeline.probe_configs", dead_probe)
    result = run(
        Options(
            config_path=str(PRODUCTION_CONFIG),
            offline_dir=str(input_dir),
            notify_enabled=False,
            quiet=True,
        )
    )

    assert result["stats"]["total"] == 0
    assert result["stats"]["quality"]["require_verified"] is True
    assert result["stats"]["quality"]["excluded_unverified"] == 1
    assert "://" not in Path("working_configs.txt").read_text(encoding="utf-8")
    assert "://" not in Path("outputs/all.txt").read_text(encoding="utf-8")
    assert "://" not in Path("outputs/best.txt").read_text(encoding="utf-8")


def test_empty_tcp_probe_keeps_previous_verified_snapshot(workspace, tmp_path, monkeypatch):
    """Users keep a usable verified URL during a transient bad probe run."""

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "source.txt").write_text(VLESS + "\n", encoding="utf-8")
    previous_plain = "#profile-title: Previous\n\n" + VLESS + "\n"
    previous_base64 = base64.b64encode(VLESS.encode("utf-8")).decode("ascii") + "\n"
    Path("outputs").mkdir()
    Path("outputs/verified.txt").write_text(previous_plain, encoding="utf-8")
    Path("outputs/verified_base64.txt").write_text(previous_base64, encoding="utf-8")

    def dead_probe(configs, settings, **_kwargs):
        for cfg in configs:
            cfg.verified = False
            cfg.latency_ms = 0
        return {
            "mode": "tcp", "endpoints_total": 1, "endpoints_probed": 1, "endpoints_cached": 0,
            "endpoints_unprobed": 0, "alive": 0, "dead": 1, "configs_alive": 0,
            "configs_dead": 1, "configs_unprobed": 0, "elapsed_ms": 1, "avg_latency_ms": 0,
        }

    monkeypatch.setattr("popvpn.pipeline.probe_configs", dead_probe)
    result = run(
        Options(
            config_path=str(PRODUCTION_CONFIG),
            offline_dir=str(input_dir),
            notify_enabled=False,
            quiet=True,
        )
    )
    assert result["stats"]["quality"]["verified_output_preserved"] is True
    assert Path("outputs/verified.txt").read_text(encoding="utf-8") == previous_plain
    assert Path("outputs/verified_base64.txt").read_text(encoding="utf-8") == previous_base64
    assert "://" not in Path("outputs/all.txt").read_text(encoding="utf-8")


def test_all_failed_sources_do_not_replace_last_successful_output(workspace, monkeypatch):
    """An upstream outage must not commit an empty replacement snapshot."""

    Path("outputs").mkdir()
    sentinel = Path("outputs/all.txt")
    sentinel.write_text("last known verified output\n", encoding="utf-8")

    def failed_fetch(self, sources):
        for source in sources:
            source.ok = False
            source.error = "simulated upstream outage"
        self.cache = type("Cache", (), {"stats": lambda _self: {}})()
        self.http_settings = None
        return {}

    monkeypatch.setattr(Pipeline, "_fetch", failed_fetch)
    result = run(
        Options(
            config_path=str(PRODUCTION_CONFIG),
            sources=["https://example.com/unavailable.txt"],
            notify_enabled=False,
            quiet=True,
        )
    )
    assert result["ok"] is False
    assert result["reason"] == "every active source failed"
    assert result["written"] == {}
    assert sentinel.read_text(encoding="utf-8") == "last known verified output\n"
