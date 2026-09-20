"""Naming / branding of configs.

Every published config gets a consistent, human readable name built from a
configurable template::

    POPVPN | 0042 | 🇩🇪 DE | VLESS | REALITY

The name is written *into* the URI (VMess entries get their encoded ``ps``
field rewritten, everything else gets its ``#fragment`` replaced) so the
client shows exactly the same name as the subscription lists.
"""

from __future__ import annotations

import re

from .protocols import Config, rename

PLACEHOLDERS = (
    "brand",
    "index",
    "flag",
    "country",
    "protocol",
    "transport",
    "security",
    "network",
    "source",
    "verified",
    "host",
    "port",
)

_WS_RE = re.compile(r"\s+")


def transport_label(cfg: Config) -> str:
    """Short human label describing how the config tunnels."""

    if cfg.security == "reality":
        return "REALITY"
    if cfg.security == "xtls":
        return "XTLS"
    network = (cfg.network or "tcp").lower()
    if network in ("ws", "websocket"):
        return "WS"
    if network in ("grpc", "gun", "multi"):
        return "GRPC"
    if network in ("h2", "http"):
        return "H2"
    if network in ("httpupgrade", "splithttp", "xhttp"):
        return network.upper()
    if network in ("kcp", "mkcp"):
        return "KCP"
    if network == "quic":
        return "QUIC"
    if cfg.protocol in ("ss", "wireguard"):
        return cfg.ss_method.upper() if cfg.ss_method else "UDP"
    if cfg.security == "tls":
        return "TLS"
    return network.upper() or "TCP"


def render_name(
    cfg: Config,
    index: int,
    *,
    template: str,
    brand: str,
    separator: str = "|",
    index_width: int = 4,
    unknown_label: str = "GLOBAL",
    max_length: int = 60,
) -> str:
    """Fill the naming template for one config."""

    values = {
        "brand": brand,
        "index": str(index).zfill(max(1, index_width)),
        "flag": cfg.geo_flag or "",
        "country": cfg.geo_code or unknown_label,
        "protocol": cfg.protocol.upper(),
        "transport": transport_label(cfg),
        "security": cfg.security.upper() if cfg.security != "none" else "",
        "network": (cfg.network or "").upper(),
        "source": cfg.source or "",
        "verified": "✔" if cfg.verified else ("✘" if cfg.verified is False else ""),
        "host": cfg.host,
        "port": str(cfg.port),
    }

    def replace(match: re.Match) -> str:
        key = match.group(1)
        return values.get(key, "")

    name = re.sub(r"\{(\w+)\}", replace, template)
    # Collapse the separators that surround empty placeholders.
    escaped = re.escape(separator)
    name = re.sub(rf"(?:\s*{escaped}\s*){{2,}}", f" {separator} ", name)
    name = re.sub(rf"^\s*{escaped}\s*|\s*{escaped}\s*$", "", name)
    name = _WS_RE.sub(" ", name).strip()
    if max_length and len(name) > max_length:
        name = name[: max_length - 1].rstrip() + "…"
    return name or f"{brand} {values['index']}"


def apply_names(
    configs: list[Config],
    *,
    template: str,
    brand: str,
    separator: str = "|",
    index_width: int = 4,
    unknown_label: str = "GLOBAL",
    max_length: int = 60,
    unique: bool = True,
) -> list[str]:
    """Name every config and return the rebuilt URIs in the same order."""

    used: dict[str, int] = {}
    uris: list[str] = []
    for index, cfg in enumerate(configs, start=1):
        name = render_name(
            cfg,
            index,
            template=template,
            brand=brand,
            separator=separator,
            index_width=index_width,
            unknown_label=unknown_label,
            max_length=max_length,
        )
        if unique:
            seen = used.get(name, 0)
            if seen:
                suffix = f" {seen + 1}"
                keep = max_length - len(suffix) if max_length else 0
                base = name[:keep].rstrip() if keep > 0 else name
                name = f"{base}{suffix}"
            used[name] = seen + 1
        cfg.name = name
        uris.append(rename(cfg.raw, name, protocol=cfg.protocol))
    return uris
