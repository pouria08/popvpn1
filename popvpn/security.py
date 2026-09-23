"""Security / hygiene audit of parsed configs.

Free feeds regularly contain configs that will simply never work, or that a
user should at least think about before trusting:

* ``allowInsecure=1`` — TLS certificate validation switched off
* legacy VMess (``v: 1``) — the pre-AEAD format, deprecated everywhere
* hosts that are loopback / private IPs
* placeholder credentials such as ``00000000-0000-0000-0000-000000000000``

The production defaults drop unsafe entries before publication. Operators can
still opt out of individual filters for controlled investigations through the
corresponding configuration setting or environment override.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field

from .protocols import Config

PLACEHOLDER_SECRETS = {
    "00000000-0000-0000-0000-000000000000",
    "12345678-1234-1234-1234-123456789abc",
    "12345678-1234-5678-1234-567812345678",
    "password",
    "secret",
    "test",
    "admin",
    "123456",
    "123456789",
}

_WEAK_SECRET_RE = re.compile(r"^(.)\1{5,}$")


@dataclass
class AuditReport:
    kept: int = 0
    dropped: int = 0
    warnings: dict = field(default_factory=dict)
    dropped_reasons: dict = field(default_factory=dict)
    insecure: int = 0
    private_hosts: int = 0
    placeholder_credentials: int = 0

    def as_dict(self) -> dict:
        return {
            "kept": self.kept,
            "dropped": self.dropped,
            "insecure": self.insecure,
            "private_hosts": self.private_hosts,
            "placeholder_credentials": self.placeholder_credentials,
            "warnings": dict(sorted(self.warnings.items(), key=lambda kv: -kv[1])),
            "dropped_reasons": self.dropped_reasons,
        }


def is_private_host(host: str) -> bool:
    """``True`` for literal loopback / private / link-local addresses."""

    if not host:
        return False
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
    )


def _weak_secret(secret: str) -> bool:
    if not secret:
        return False
    lowered = secret.strip().lower()
    if lowered in PLACEHOLDER_SECRETS:
        return True
    if _WEAK_SECRET_RE.match(lowered):
        return True
    digits = sum(char.isdigit() for char in lowered)
    return len(lowered) >= 6 and digits == len(lowered) and len(set(lowered)) <= 3


def audit(configs: list[Config], settings: dict | None = None) -> tuple[list[Config], AuditReport]:
    """Tag (and optionally drop) risky configs.  Returns ``(kept, report)``."""

    settings = settings or {}
    # The library is observational when called without settings. Production
    # strictness comes from config.yaml, which supplies explicit true values;
    # this keeps ``audit(configs)`` useful for diagnostics and integrations.
    drop_insecure = bool(settings.get("drop_insecure", False))
    drop_private = bool(settings.get("drop_private_hosts", False))
    drop_legacy = bool(settings.get("drop_legacy_vmess", False))
    drop_weak_credentials = bool(settings.get("drop_weak_credentials", False))
    max_warnings = int(settings.get("max_warnings", 99))

    report = AuditReport()
    kept: list[Config] = []

    for cfg in configs:
        if is_private_host(cfg.host):
            if "private-host" not in cfg.warnings:
                cfg.warnings.append("private-host")
            report.private_hosts += 1
        if _weak_secret(cfg.secret):
            if "weak-credential" not in cfg.warnings:
                cfg.warnings.append("weak-credential")
            report.placeholder_credentials += 1
        if "allow-insecure" in cfg.warnings or cfg.legacy:
            report.insecure += 1

        for warning in set(cfg.warnings):
            report.warnings[warning] = report.warnings.get(warning, 0) + 1

        reasons = []
        if drop_private and is_private_host(cfg.host):
            reasons.append("private-host")
        if drop_insecure and (
            "allow-insecure" in cfg.warnings or "tls-disabled" in cfg.warnings
        ):
            reasons.append("insecure")
        if drop_legacy and cfg.legacy:
            reasons.append("legacy-vmess")
        if drop_weak_credentials and "weak-credential" in cfg.warnings:
            reasons.append("weak-credential")
        if len(set(cfg.warnings)) > max_warnings:
            reasons.append("too-many-warnings")

        if reasons:
            report.dropped += 1
            for reason in reasons:
                report.dropped_reasons[reason] = report.dropped_reasons.get(reason, 0) + 1
            continue
        kept.append(cfg)

    report.kept = len(kept)
    return kept, report
