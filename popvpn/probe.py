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
    """Runtime settings for liveness checks.

    TCP is deliberately the default: it is safe for every supported transport,
    including Reality, and answers the only publication question we need here:
    whether the advertised endpoint accepts a connection right now.
    """

    mode: str = "tcp"
    workers: int = 128
    timeout: float = 4.0
    tls: bool = False
    max_endpoints: int = 12000
    cache_ttl: int = 900
    state_file: str = "state/probe_cache.json"
    persist: bool = True


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

    def get(self, endpoint: str, mode: str) -> dict | None:
        """Return a fresh verdict produced with the same probe mode.

        Older cache files did not include a mode. They are intentionally
        treated as stale so a TCP run never mistakes a former TLS result for a
        current TCP liveness check.
        """

        entry = self.entries.get(endpoint)
        if not entry or entry.get("mode") != mode:
            return None
        if time.time() - float(entry.get("at", 0)) > self.ttl:
            return None
        return entry

    def put(self, endpoint: str, mode: str, ok: bool, ms: int) -> dict:
        entry = {"mode": mode, "ok": bool(ok), "ms": int(ms), "at": int(time.time())}
        self.entries[endpoint] = entry
        return entry

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
    """Probe unique endpoints and annotate every config in place.

    A verdict is only used when it is fresh *and* was produced in the requested
    mode. Endpoints above ``max_endpoints`` remain explicitly unverified;
    callers that require verified output can therefore filter safely instead
    of accidentally publishing an untested configuration.
    """

    mode = (settings.mode or "tcp").strip().lower()
    # A malformed environment override must fail closed. Falling back to TCP
    # preserves the production guarantee rather than quietly skipping probes.
    if mode not in {"off", "tcp", "tls"}:
        mode = "tcp"
    summary = {
        "mode": mode,
        "endpoints_total": 0,
        "endpoints_probed": 0,
        "endpoints_cached": 0,
        "endpoints_unprobed": 0,
        "alive": 0,
        "dead": 0,
        "configs_alive": 0,
        "configs_dead": 0,
        "configs_unprobed": 0,
        "elapsed_ms": 0,
        "avg_latency_ms": 0,
    }
    if mode == "off" or not configs:
        return summary

    use_tls = mode == "tls"
    cache = ProbeCache(settings.state_file, settings.cache_ttl)
    endpoints: dict[str, str] = {}
    endpoint_scores: dict[str, float] = {}
    for cfg in configs:
        if not cfg.host or not cfg.port:
            continue
        endpoints.setdefault(cfg.endpoint, cfg.sni or cfg.host)
        endpoint_scores[cfg.endpoint] = max(endpoint_scores.get(cfg.endpoint, 0.0), cfg.score)

    summary["endpoints_total"] = len(endpoints)
    verdicts: dict[str, dict] = {}
    todo: list[tuple[str, str]] = []
    for endpoint, sni in endpoints.items():
        cached = cache.get(endpoint, mode)
        if cached is not None:
            verdicts[endpoint] = cached
            summary["endpoints_cached"] += 1
        else:
            todo.append((endpoint, sni))

    # When a safety cap is needed, spend the budget on higher-quality
    # candidates first. The endpoint name is a stable tie-breaker.
    todo.sort(key=lambda item: (-endpoint_scores.get(item[0], 0.0), item[0]))
    todo = todo[: max(0, settings.max_endpoints)]
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
                for endpoint, sni in todo
            }
            for done, future in enumerate(as_completed(futures), start=1):
                endpoint = futures[future]
                try:
                    ok, ms = future.result()
                except Exception:  # pragma: no cover - defensive
                    ok, ms = False, 0
                verdicts[endpoint] = cache.put(endpoint, mode, ok, ms)
                if on_progress and (done % 250 == 0 or done == len(todo)):
                    on_progress(done, len(todo))
        if settings.persist:
            cache.prune()
            cache.save()

    summary["endpoints_unprobed"] = summary["endpoints_total"] - len(verdicts)
    latencies: list[int] = []
    for entry in verdicts.values():
        ok = bool(entry.get("ok"))
        ms = int(entry.get("ms", 0))
        if ok:
            summary["alive"] += 1
            latencies.append(ms)
        else:
            summary["dead"] += 1

    for cfg in configs:
        entry = verdicts.get(cfg.endpoint)
        if entry is None:
            cfg.verified = None
            cfg.latency_ms = None
            summary["configs_unprobed"] += 1
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
