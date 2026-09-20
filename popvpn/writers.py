"""Output generation.

One pipeline run produces every artefact a client or a human could want:

===============================  ============================================
``working_configs.txt``          mixed plain text (Hiddify metadata header)
``base64.txt``                   the same list, Base64 encoded
``stats.txt``                    human readable statistics
``outputs/all.txt``              mixed plain text
``outputs/all_base64.txt``       mixed Base64
``outputs/by-protocol/*.txt``    one file per protocol (+ ``*_base64.txt``)
``outputs/by-country/XX.txt``    one file per detected country
``outputs/best.txt``             top-N configs by quality score
``outputs/verified.txt``         only configs that answered the probe
``outputs/clash.yaml``           Clash / Mihomo compatible proxy list
``outputs/singbox.json``         sing-box ``outbounds`` import file
``outputs/stats.json``           machine readable statistics
``outputs/sources.json``         per-source health
===============================  ============================================
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from pathlib import Path

from .protocols import Config

ROOT_FILES = ("working_configs.txt", "base64.txt", "stats.txt")


@dataclass
class Written:
    files: dict = field(default_factory=dict)

    def add(self, path: Path, content: str | bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        self.files[str(path)] = path.stat().st_size

    @property
    def total_bytes(self) -> int:
        return sum(self.files.values())


# ---------------------------------------------------------------------------
# Subscription header
# ---------------------------------------------------------------------------


def profile_header(profile: dict) -> list[str]:
    """Hiddify / v2rayNG compatible metadata header."""

    lines = [
        f"#profile-title: {profile.get('title', 'POPVPN X')}",
        f"#profile-update-interval: {profile.get('update_interval', 1)}",
        (
            "#subscription-userinfo: upload=0; download=0; "
            f"total={profile.get('total', 10737418240000000)}; "
            f"expire={profile.get('expire', 2546249531)}"
        ),
    ]
    if profile.get("profile_web_page_url"):
        lines.append(f"#profile-web-page-url: {profile['profile_web_page_url']}")
    if profile.get("support_url"):
        lines.append(f"#support-url: {profile['support_url']}")
    if profile.get("client_types"):
        lines.append(f"#client-types: {profile['client_types']}")
    if profile.get("announce"):
        lines.append(f"#announce: {profile['announce']}")
    lines.append("")
    return lines


def plain_subscription(uris: list[str], profile: dict | None = None) -> str:
    header = profile_header(profile or {})
    return "\n".join(header + list(uris)).rstrip() + "\n"


def base64_subscription(uris: list[str]) -> str:
    payload = "\n".join(uris)
    return base64.b64encode(payload.encode("utf-8")).decode("ascii") + "\n"


# ---------------------------------------------------------------------------
# Clash / Mihomo
# ---------------------------------------------------------------------------

_NEEDS_QUOTING = set(":#{}[],&*!|>'\"%@`")


def _yaml_scalar(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    if text.strip() != text or any(char in _NEEDS_QUOTING for char in text):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    lowered = text.lower()
    if lowered in ("true", "false", "null", "yes", "no", "on", "off", "~"):
        return f'"{text}"'
    try:
        float(text)
        return f'"{text}"'
    except ValueError:
        return text


def _yaml_dump(value, indent: int = 0) -> list[str]:
    pad = "  " * indent
    lines: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{pad}{key}:")
                lines.extend(_yaml_dump(item, indent + 1))
            elif isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}: {'{}' if isinstance(item, dict) else '[]'}")
            else:
                lines.append(f"{pad}{key}: {_yaml_scalar(item)}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                nested = _yaml_dump(item, indent + 1)
                if nested:
                    first = nested[0].strip()
                    lines.append(f"{pad}- {first}")
                    lines.extend(nested[1:])
                else:  # pragma: no cover - empty dict
                    lines.append(f"{pad}- {{}}")
            elif isinstance(item, list):
                lines.append(f"{pad}-")
                lines.extend(_yaml_dump(item, indent + 1))
            else:
                lines.append(f"{pad}- {_yaml_scalar(item)}")
    else:  # pragma: no cover - top level is always a container
        lines.append(f"{pad}{_yaml_scalar(value)}")
    return lines


def _ws_opts(cfg: Config) -> dict:
    opts: dict = {}
    path = cfg.params.get("path") or ""
    if path:
        opts["path"] = path
    host = cfg.sni or cfg.params.get("host") or ""
    if host:
        opts["headers"] = {"Host": host}
    max_early = cfg.params.get("ed") or cfg.params.get("earlydata")
    if max_early:
        opts["max-early-data"] = int(max_early) if str(max_early).isdigit() else 1024
        opts["early-data-header-name"] = "Sec-WebSocket-Protocol"
    return opts


def clash_proxy(cfg: Config) -> dict | None:
    """Translate one config into a Clash / Mihomo proxy entry."""

    name = cfg.name or cfg.remark or cfg.host
    base = {"name": name, "server": cfg.host, "port": cfg.port}
    params = cfg.params
    network = (cfg.network or "tcp").lower()
    insecure = "allow-insecure" in cfg.warnings

    if cfg.protocol == "vless":
        proxy = {**base, "type": "vless", "uuid": cfg.secret, "udp": True}
        if cfg.security in ("tls", "reality", "xtls"):
            proxy["tls"] = True
        if cfg.sni:
            proxy["servername"] = cfg.sni
        flow = params.get("flow")
        if flow:
            proxy["flow"] = flow
        fingerprint = params.get("fp") or params.get("fingerprint")
        if cfg.security == "reality":
            proxy["client-fingerprint"] = fingerprint or "chrome"
            reality = {}
            if params.get("pbk"):
                reality["public-key"] = params["pbk"]
            if params.get("sid"):
                reality["short-id"] = params["sid"]
            if reality:
                proxy["reality-opts"] = reality
        elif fingerprint:
            proxy["client-fingerprint"] = fingerprint
        if params.get("encryption") and params["encryption"] != "none":
            proxy["xudp"] = True
    elif cfg.protocol == "vmess":
        data = cfg.vmess_json or {}
        proxy = {
            **base,
            "type": "vmess",
            "uuid": cfg.secret,
            "alterId": int(data.get("aid") or 0) if str(data.get("aid", "0")).isdigit() else 0,
            "cipher": data.get("scy") or "auto",
            "udp": True,
        }
        if cfg.security == "tls":
            proxy["tls"] = True
        if cfg.sni:
            proxy["servername"] = cfg.sni
    elif cfg.protocol == "trojan":
        proxy = {**base, "type": "trojan", "password": cfg.secret, "udp": True}
        if cfg.sni:
            proxy["sni"] = cfg.sni
        if insecure:
            proxy["skip-cert-verify"] = True
    elif cfg.protocol == "ss":
        proxy = {**base, "type": "ss", "cipher": cfg.ss_method, "password": cfg.secret, "udp": True}
        if params.get("plugin") and params.get("plugin-opts"):
            proxy["plugin"] = params["plugin"]
            proxy["plugin-opts"] = params["plugin-opts"]
    elif cfg.protocol == "tuic":
        proxy = {
            **base,
            "type": "tuic",
            "uuid": cfg.secret,
            "password": params.get("password", ""),
            "udp": True,
        }
        if cfg.sni:
            proxy["sni"] = cfg.sni
        if params.get("congestion-control"):
            proxy["congestion-control"] = params["congestion-control"]
        if insecure:
            proxy["skip-cert-verify"] = True
    elif cfg.protocol in ("hy2", "hysteria"):
        proxy = {**base, "type": "hysteria2", "password": cfg.secret, "udp": True}
        if cfg.sni:
            proxy["sni"] = cfg.sni
        if insecure:
            proxy["skip-cert-verify"] = True
        if params.get("obfs") and params.get("obfs-password"):
            proxy["obfs"] = params["obfs"]
            proxy["obfs-password"] = params["obfs-password"]
    elif cfg.protocol == "wireguard":
        proxy = {
            **base,
            "type": "wireguard",
            "public-key": params.get("publickey") or cfg.secret,
            "private-key": params.get("privatekey", ""),
            "udp": True,
        }
        if params.get("address"):
            proxy["ip"] = params["address"].split(",")[0].split("/")[0]
        if params.get("preshared-key"):
            proxy["preshared-key"] = params["preshared-key"]
    else:  # pragma: no cover - registry guard
        return None

    if network in ("ws", "websocket"):
        proxy["network"] = "ws"
        opts = _ws_opts(cfg)
        if opts:
            proxy["ws-opts"] = opts
    elif network in ("grpc", "gun", "multi"):
        proxy["network"] = "grpc"
        service = params.get("servicename") or params.get("path") or ""
        if service:
            proxy["grpc-opts"] = {"grpc-service-name": service}
    elif network in ("h2", "http"):
        proxy["network"] = "h2"
        opts = _ws_opts(cfg)
        if opts:
            proxy["h2-opts"] = opts
    elif network in ("httpupgrade",):
        proxy["network"] = "httpupgrade"
        opts = _ws_opts(cfg)
        if opts:
            proxy["httpupgrade-opts"] = opts

    proxy.setdefault("udp", True)
    return proxy


def clash_document(configs: list[Config], profile: dict | None = None) -> str:
    """Full Clash / Mihomo config: proxies, groups, rules."""

    profile = profile or {}
    proxies = []
    for cfg in configs:
        proxy = clash_proxy(cfg)
        if proxy:
            proxies.append(proxy)
    names = [proxy["name"] for proxy in proxies]

    by_protocol: dict[str, list[str]] = {}
    for cfg, proxy in zip(configs, proxies):
        by_protocol.setdefault(cfg.protocol, []).append(proxy["name"])

    groups: list[dict] = [
        {
            "name": "AUTO",
            "type": "url-test",
            "proxies": names[:200],
            "url": "https://www.gstatic.com/generate_204",
            "interval": 300,
            "tolerance": 50,
        },
        {"name": "SELECT", "type": "select", "proxies": ["AUTO"] + names[:100]},
    ]
    for protocol, protocol_names in sorted(by_protocol.items()):
        groups.append(
            {
                "name": protocol.upper(),
                "type": "url-test",
                "proxies": protocol_names[:100],
                "url": "https://www.gstatic.com/generate_204",
                "interval": 300,
            }
        )

    document = {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "info",
        "ipv6": False,
        "unified-delay": True,
        "tcp-concurrent": True,
        "profile": {
            "store-selected": True,
            "store-fake-ip": True,
        },
        "dns": {
            "enable": True,
            "ipv6": False,
            "enhanced-mode": "fake-ip",
            "fake-ip-range": "198.18.0.1/16",
            "nameserver": ["https://dns.google/dns-query", "https://1.1.1.1/dns-query"],
            "fallback": ["https://8.8.4.4/dns-query", "tls://9.9.9.9:853"],
        },
        "proxies": proxies,
        "proxy-groups": groups,
        "rules": [
            "GEOIP,LAN,DIRECT,no-resolve",
            "GEOIP,IR,DIRECT",
            "MATCH,SELECT",
        ],
    }
    header = [
        f"# {profile.get('title', 'POPVPN X')} — Clash / Mihomo profile",
        f"# generated: {profile.get('generated_at', '')}",
        f"# configs: {len(proxies)}",
        "",
    ]
    return "\n".join(header + _yaml_dump(document)) + "\n"


# ---------------------------------------------------------------------------
# sing-box
# ---------------------------------------------------------------------------


def singbox_outbound(cfg: Config) -> dict | None:
    name = cfg.name or cfg.remark or cfg.host
    base = {"tag": name, "server": cfg.host, "server_port": cfg.port}
    params = cfg.params
    network = (cfg.network or "tcp").lower()
    transport = None
    if network in ("ws", "websocket"):
        transport = {"type": "ws"}
        if params.get("path"):
            transport["path"] = params["path"]
        if cfg.sni:
            transport["headers"] = {"Host": cfg.sni}
    elif network in ("grpc", "gun", "multi"):
        transport = {"type": "grpc"}
        service = params.get("servicename") or params.get("path")
        if service:
            transport["service_name"] = service
    elif network in ("httpupgrade",):
        transport = {"type": "httpupgrade"}

    def tls_block(reality: bool) -> dict:
        block: dict = {"enabled": True}
        if cfg.sni:
            block["server_name"] = cfg.sni
        fingerprint = params.get("fp") or params.get("fingerprint")
        if fingerprint:
            block["utls"] = {"enabled": True, "fingerprint": fingerprint}
        if reality:
            inner: dict = {"enabled": True}
            if params.get("pbk"):
                inner["public_key"] = params["pbk"]
            if params.get("sid"):
                inner["short_id"] = params["sid"]
            block["reality"] = inner
        if "allow-insecure" in cfg.warnings:
            block["insecure"] = True
        return block

    if cfg.protocol == "vless":
        out = {**base, "type": "vless", "uuid": cfg.secret}
        if params.get("flow"):
            out["flow"] = params["flow"]
        if cfg.security in ("tls", "reality"):
            out["tls"] = tls_block(cfg.security == "reality")
    elif cfg.protocol == "vmess":
        data = cfg.vmess_json or {}
        out = {
            **base,
            "type": "vmess",
            "uuid": cfg.secret,
            "security": data.get("scy") or "auto",
            "alter_id": int(data.get("aid") or 0) if str(data.get("aid", "0")).isdigit() else 0,
        }
        if cfg.security == "tls":
            out["tls"] = tls_block(False)
    elif cfg.protocol == "trojan":
        out = {**base, "type": "trojan", "password": cfg.secret}
        out["tls"] = tls_block(False)
    elif cfg.protocol == "ss":
        out = {**base, "type": "shadowsocks", "method": cfg.ss_method, "password": cfg.secret}
    elif cfg.protocol == "tuic":
        out = {
            **base,
            "type": "tuic",
            "uuid": cfg.secret,
            "password": params.get("password", ""),
            "tls": tls_block(False),
        }
        if params.get("congestion-control"):
            out["congestion_control"] = params["congestion-control"]
    elif cfg.protocol in ("hy2", "hysteria"):
        out = {**base, "type": "hysteria2", "password": cfg.secret, "tls": tls_block(False)}
    elif cfg.protocol == "wireguard":
        out = {
            **base,
            "type": "wireguard",
            "private_key": params.get("privatekey", ""),
            "peer_public_key": params.get("publickey", ""),
            "local_address": [params.get("address", "172.16.0.2/32")],
        }
    else:  # pragma: no cover
        return None
    if transport:
        out["transport"] = transport
    return out


def singbox_document(configs: list[Config], profile: dict | None = None) -> str:
    profile = profile or {}
    outbounds = [ob for ob in (singbox_outbound(cfg) for cfg in configs) if ob]
    tags = [ob["tag"] for ob in outbounds]
    document = {
        "log": {"level": "warn", "timestamp": True},
        "dns": {
            "servers": [
                {"tag": "remote", "address": "https://1.1.1.1/dns-query", "detour": "select"},
                {"tag": "local", "address": "https://8.8.8.8/dns-query", "detour": "direct"},
            ],
            "rules": [{"outbound": "any", "server": "local"}],
            "final": "remote",
        },
        "outbounds": [
            {"tag": "select", "type": "selector", "outbounds": tags[:200] or ["direct"]},
            {"tag": "direct", "type": "direct"},
            {"tag": "block", "type": "block"},
            {"tag": "dns", "type": "dns"},
        ]
        + outbounds,
        "route": {
            "rules": [
                {"protocol": "dns", "outbound": "dns"},
                {"ip_is_private": True, "outbound": "direct"},
                {"geoip": ["ir"], "outbound": "direct"},
            ],
            "final": "select",
            "auto_detect_interface": True,
        },
        "_meta": {
            "title": profile.get("title", "POPVPN X"),
            "generated_at": profile.get("generated_at", ""),
            "count": len(outbounds),
        },
    }
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


# ---------------------------------------------------------------------------
# Grouping helpers
# ---------------------------------------------------------------------------


def group_by_protocol(configs: list[Config], uris: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for cfg, uri in zip(configs, uris):
        groups.setdefault(cfg.protocol, []).append(uri)
    return groups


def group_by_country(configs: list[Config], uris: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for cfg, uri in zip(configs, uris):
        groups.setdefault(cfg.geo_code or "GLOBAL", []).append(uri)
    return groups
