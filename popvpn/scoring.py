"""Quality scoring.

A free feed is mostly noise: the same server published by five sources, half
of it dead, some of it insecure.  Scoring gives every config a comparable
0-100 number so the pipeline can publish a "best of" list, sort sensibly and
let the dashboard show why a config ranks where it does.
"""

from __future__ import annotations

from .protocols import Config

PROTOCOL_WEIGHT = {
    "vless": 12.0,
    "hy2": 12.0,
    "trojan": 11.0,
    "tuic": 11.0,
    "vmess": 9.0,
    "ss": 9.0,
    "wireguard": 7.0,
    "hysteria": 8.0,
}

SECURITY_BONUS = {"reality": 26.0, "tls": 16.0, "xtls": 14.0, "none": 0.0}
NETWORK_BONUS = {
    "ws": 4.0, "websocket": 4.0, "grpc": 5.0, "gun": 5.0, "multi": 5.0,
    "h2": 4.0, "http": 3.0, "httpupgrade": 4.0, "splithttp": 4.0,
    "xhttp": 4.0, "tcp": 2.0, "raw": 2.0, "quic": 2.0, "kcp": 1.0,
    "mkcp": 1.0, "udp": 1.0,
}

WARNING_PENALTY = {
    "allow-insecure": 22.0,
    "tls-disabled": 10.0,
    "legacy-vmess": 28.0,
    "unknown-ss-method": 8.0,
    "unknown-network": 3.0,
    "unknown-security": 3.0,
    "plugin": 4.0,
    "private-host": 30.0,
    "duplicate-uuid": 6.0,
}

MAX_SCORE = 100.0


def score(cfg: Config, *, source_reliability: float = 1.0) -> float:
    """Return a 0-100 quality score for ``cfg`` (also stored on the config)."""

    total = 10.0
    total += PROTOCOL_WEIGHT.get(cfg.protocol, 5.0)
    total += SECURITY_BONUS.get(cfg.security, 0.0)
    total += NETWORK_BONUS.get((cfg.network or "").lower(), 0.0)
    if cfg.sni:
        total += 4.0
    if cfg.params.get("alpn"):
        total += 2.0
    if cfg.params.get("fp") or cfg.params.get("fingerprint"):
        total += 2.0
    if cfg.params.get("mux") in ("true", "1"):
        total += 1.0
    if cfg.geo_code:
        total += 6.0
    for warning in set(cfg.warnings):
        total -= WARNING_PENALTY.get(warning, 5.0)
    reliability = max(0.0, min(1.0, source_reliability))
    total += (reliability - 0.5) * 12.0

    if cfg.verified is True:
        total += 30.0
        if cfg.latency_ms is not None:
            total += max(0.0, 12.0 - cfg.latency_ms / 60.0)
    elif cfg.verified is False:
        total -= 45.0

    cfg.score = round(max(0.0, min(MAX_SCORE, total)), 2)
    return cfg.score


def score_all(configs: list[Config], reliability_of=None) -> None:
    lookup = reliability_of or (lambda _url: 1.0)
    for cfg in configs:
        score(cfg, source_reliability=lookup(cfg.source))


def sort_configs(configs: list[Config], mode: str = "score") -> list[Config]:
    """Stable, deterministic ordering — the same input always yields the same file."""

    if mode == "protocol":
        return sorted(configs, key=lambda c: (c.protocol, -c.score, c.host, c.port))
    if mode == "country":
        return sorted(configs, key=lambda c: (c.geo_code or "ZZ", -c.score, c.host, c.port))
    if mode == "latency":
        return sorted(
            configs,
            key=lambda c: (c.verified is False, c.latency_ms if c.latency_ms is not None else 10**6),
        )
    return sorted(configs, key=lambda c: (-c.score, c.protocol, c.host, c.port, c.name))
