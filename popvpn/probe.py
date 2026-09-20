"""Liveness probing.

Most published configs are dead.  Instead of trusting the feed, the pipeline
can check every *unique* ``host:port`` once (a config list of 10k entries is
usually only ~1-3k distinct endpoints) and mark the results:

* ``tcp`` — a plain TCP connect
* ``tls`` — TCP connect plus a TLS handshake with SNI (only meaningful for
  plain-TLS transports; Reality servers deliberately reject a normal TLS
  handshake, so those are probed with TCP)

Verdicts are cached in ``state/probe_cache.json`` so an hourly run only pays
for the endpoints it has not seen recently.
"""

from __future__ import annotations

import contextlib
import json
import socket
import ssl
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from .protocols import Config


@dataclass
class ProbeSettings:
    mode: str = "off"
    workers: int = 96
    timeout: float = 4.0
    tls: bool = False
    max_endpoints: int = 4000
    cache_ttl: int = 3600
    state_file: str = "state/probe_cache.json"


class ProbeCache:
    def __init__(self, path: str | Path, ttl: int = 3600) -> None:
        self.path = Path(path)
        self.ttl = int(ttl)
        self.entries: dict[str, dict] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if isinstance(data, dict):
            self.entries = {k: v for k, v in data.get("endpoints", {}).items() if isinstance(v, dict)}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"updated_at": int(time.time()), "endpoints": self.entries}, indent=0),
            encoding="utf-8",
        )

    def get(self, endpoint: str) -> dict | None:
        entry = self.entries.get(endpoint)
        if not entry:
            return None
        if time.time() - float(entry.get("at", 0)) > self.ttl:
            return None
        return entry

    def put(self, endpoint: str, ok: bool, ms: int) -> None:
        self.entries[endpoint] = {"ok": bool(ok), "ms": int(ms), "at": int(time.time())}

    def prune(self, keep: int = 20000) -> None:
        if len(self.entries) <= keep:
            return
        self.entries = dict(
            sorted(self.entries.items(), key=lambda kv: -kv[1].get("at", 0))[:keep]
        )


def _probe_endpoint(endpoint: str, timeout: float, use_tls: bool, sni: str = "") -> tuple[bool, int]:
    host, _, port_text = endpoint.rpartition(":")
    host = host.strip("[]")
    try:
        port = int(port_text)
    except ValueError:
        return False, 0
    started = time.monotonic()
    sock = None
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        if use_tls:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock.settimeout(timeout)
            with context.wrap_socket(sock, server_hostname=sni or host) as tls_sock:
                tls_sock.do_handshake()
                sock = None
        elapsed = int((time.monotonic() - started) * 1000)
        return True, elapsed
    except (OSError, ssl.SSLError, socket.timeout, ValueError):
        return False, int((time.monotonic() - started) * 1000)
    finally:
        if sock is not None:
            with contextlib.suppress(OSError):  # pragma: no cover - defensive
                sock.close()


def _needs_tls(cfg: Config) -> bool:
    if cfg.security in ("reality", "xtls"):
        return False
    return cfg.security == "tls" or cfg.protocol in ("trojan", "tuic", "hy2", "hysteria")


def probe_configs(
    configs: list[Config],
    settings: ProbeSettings,
    *,
    on_progress=None,
) -> dict:
    """Probe every unique endpoint and annotate the configs in place."""

    summary = {
        "mode": settings.mode,
        "endpoints_total": 0,
        "endpoints_probed": 0,
        "endpoints_cached": 0,
        "alive": 0,
        "dead": 0,
        "configs_alive": 0,
        "configs_dead": 0,
        "elapsed_ms": 0,
        "avg_latency_ms": 0,
    }
    if settings.mode == "off" or not configs:
        return summary

    use_tls = settings.mode == "tls"
    cache = ProbeCache(settings.state_file, settings.cache_ttl)
    endpoints: dict[str, str] = {}
    for cfg in configs:
        if cfg.host and cfg.port:
            endpoints.setdefault(cfg.endpoint, cfg.sni or cfg.host)

    summary["endpoints_total"] = len(endpoints)
    todo: dict[str, str] = {}
    for endpoint, sni in endpoints.items():
        cached = cache.get(endpoint)
        if cached:
            summary["endpoints_cached"] += 1
            continue
        todo[endpoint] = sni

    todo = dict(list(todo.items())[: max(0, settings.max_endpoints)])
    summary["endpoints_probed"] = len(todo)
    started = time.monotonic()

    # An endpoint is only TLS-probed when nothing on it needs a plain TCP
    # handshake (Reality servers answer a normal TLS ClientHello by dropping
    # the connection, so probing them with TLS would mark them dead).
    plain_endpoints = {cfg.endpoint for cfg in configs if not _needs_tls(cfg)}

    if todo:
        workers = max(1, min(settings.workers, len(todo)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _probe_endpoint,
                    endpoint,
                    settings.timeout,
                    use_tls and endpoint not in plain_endpoints,
                    sni,
                ): endpoint
                for endpoint, sni in todo.items()
            }
            for done, future in enumerate(as_completed(futures), start=1):
                endpoint = futures[future]
                try:
                    ok, ms = future.result()
                except Exception:  # pragma: no cover - defensive
                    ok, ms = False, 0
                cache.put(endpoint, ok, ms)
                if on_progress and done % 250 == 0:
                    on_progress(done, len(todo))
        cache.prune()
        cache.save()

    latencies: list[int] = []
    for endpoint in endpoints:
        entry = cache.entries.get(endpoint)
        ok = bool(entry and entry.get("ok"))
        ms = int(entry.get("ms", 0)) if entry else 0
        if ok:
            summary["alive"] += 1
            latencies.append(ms)
        else:
            summary["dead"] += 1

    for cfg in configs:
        entry = cache.entries.get(cfg.endpoint)
        if entry is None:
            continue
        cfg.verified = bool(entry.get("ok"))
        cfg.latency_ms = int(entry.get("ms", 0))
        if cfg.verified:
            summary["configs_alive"] += 1
        else:
            summary["configs_dead"] += 1

    summary["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    summary["avg_latency_ms"] = int(sum(latencies) / len(latencies)) if latencies else 0
    return summary

