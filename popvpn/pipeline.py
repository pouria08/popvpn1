"""The pipeline: fetch → parse → dedupe → geo → audit → score → probe → publish."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, geo, naming, scoring, writers
from .cache import HttpCache
from .config import Config
from .http import FetchResult, HttpSettings, fetch_many
from .notify import notify
from .probe import ProbeSettings, probe_configs
from .protocols import Config as VpnConfig
from .protocols import decode_body, extract_uris, looks_like_error_page, parse_uri
from .security import audit
from .sources import Source, SourceHealth, load_sources, parse_links
from .stats import (
    build_run_entry,
    inject_readme,
    load_history,
    render_markdown,
    render_stats_txt,
    save_history,
    sparkline_svg,
)


@dataclass
class Options:
    config_path: str = "config.yaml"
    dry_run: bool = False
    limit: int = 0
    probe: str = ""
    workers: int = 0
    sources: list = field(default_factory=list)
    offline_dir: str = ""
    outputs_dir: str = ""
    no_cache: bool = False
    keep_history: bool = True
    write_readme: bool = True
    notify_enabled: bool = True
    verbose: bool = False
    quiet: bool = False


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class Pipeline:
    def __init__(self, options: Options | None = None) -> None:
        self.options = options or Options()
        self.cfg = Config.load(self.options.config_path)
        self.log_lines: list[str] = []

    # -- logging ---------------------------------------------------------
    def log(self, message: str) -> None:
        self.log_lines.append(message)
        if not self.options.quiet:
            print(message, flush=True)

    # -- sources ---------------------------------------------------------
    def _load_sources(self) -> list[Source]:
        if self.options.sources:
            return parse_links("\n".join(self.options.sources))
        if self.options.offline_dir:
            # ``--offline DIR`` is self-contained: every file in DIR becomes
            # a source, so no links.txt is needed for local/test runs.
            return self._offline_sources()
        sources_file = self.cfg.get("sources.file", "links.txt")
        return load_sources(sources_file)

    def _offline_sources(self) -> list[Source]:
        directory = Path(self.options.offline_dir)
        if not directory.is_dir():
            raise FileNotFoundError(f"offline directory not found: {directory}")
        files = sorted(path for path in directory.iterdir() if path.is_file())
        if not files:
            raise FileNotFoundError(f"no input files found in {directory}")
        return [
            Source(url=f"file://{path.name}", name=path.stem, ok=True) for path in files
        ]

    def _offline_bodies(self, sources: list[Source]) -> dict[str, str]:
        directory = Path(self.options.offline_dir)
        bodies: dict[str, str] = {}
        for source in sources:
            path = directory / source.url.split("file://", 1)[1]
            bodies[source.url] = path.read_text(encoding="utf-8", errors="replace")
            source.ok = True
            source.status = 200
        return bodies

    # -- fetching --------------------------------------------------------
    def _fetch(self, sources: list[Source]) -> dict[str, str]:
        cache_dir = self.cfg.get("fetch.cache_dir", ".cache/http")
        cache = HttpCache(
            cache_dir,
            ttl=int(self.cfg.get("fetch.cache_ttl", 900)),
            enabled=bool(self.cfg.get("fetch.use_cache", True)) and not self.options.no_cache,
            writable=not self.options.dry_run,
        )
        self.cache = cache

        settings = HttpSettings(
            connect_timeout=float(self.cfg.get("fetch.connect_timeout", 10)),
            read_timeout=float(self.cfg.get("fetch.read_timeout", 45)),
            retries=int(self.cfg.get("fetch.retries", 3)),
            backoff=float(self.cfg.get("fetch.backoff", 1.6)),
            jitter=float(self.cfg.get("fetch.jitter", 0.35)),
            max_bytes=int(self.cfg.get("fetch.max_bytes", 26_214_400)),
            user_agent=str(self.cfg.get("fetch.user_agent", "POPVPN-X")),
        )
        self.http_settings = settings

        bodies: dict[str, str] = {}
        pending: list[Source] = []
        for source in sources:
            hit = cache.get(source.url)
            if hit:
                body, _meta = hit
                bodies[source.url] = body
                source.ok = True
                source.status = 200
                source.from_cache = True
                continue
            pending.append(source)

        if pending:
            workers = self.options.workers or int(self.cfg.get("fetch.workers", 12))
            etags = {source.url: cache.validators(source.url) for source in pending}
            results: dict[str, FetchResult] = fetch_many(
                [source.url for source in pending], settings, workers=workers, etags=etags
            )
            use_stale = bool(self.cfg.get("fetch.use_stale_on_error", True))
            for source in pending:
                result = results.get(source.url) or FetchResult(url=source.url, error="no result")
                source.elapsed_ms = result.elapsed_ms
                source.status = result.status
                if result.ok and result.status == 304:
                    cache.touch(source.url)
                    stored = cache.stored_body(source.url)
                    if stored is not None:
                        bodies[source.url] = stored
                        source.ok = True
                        source.from_cache = True
                        continue
                if result.ok:
                    bodies[source.url] = result.text
                    source.ok = True
                    cache.put(source.url, result.text, result.headers)
                    continue
                source.error = result.error
                if use_stale:
                    stored = cache.stored_body(source.url)
                    if stored:
                        bodies[source.url] = stored
                        source.from_cache = True
                        source.error = f"{result.error} (using cached body)"
                        source.ok = True
        return bodies

    # -- main ------------------------------------------------------------
    def run(self) -> dict:
        started = time.monotonic()
        options = self.options
        sources = self._load_sources()
        health = SourceHealth(
            self.cfg.get("sources.state_file", "state/sources.json"),
            max_failures=int(self.cfg.get("sources.max_failures", 3)),
            revive_after_hours=float(self.cfg.get("sources.revive_after_hours", 6)),
        )
        removed_health_records = health.retain(source.url for source in sources)
        if removed_health_records:
            self.log(f"[popvpn] removed {removed_health_records} obsolete source-health record(s)")

        paused: list[Source] = []
        active: list[Source] = []
        for source in sources:
            if not source.enabled:
                continue
            if health.is_paused(source.url):
                source.error = "auto-paused after repeated failures"
                paused.append(source)
                continue
            active.append(source)

        self.log(
            f"[popvpn] v{__version__} · sources: {len(active)} active, "
            f"{len(paused)} paused, {len(sources) - len(active) - len(paused)} disabled"
        )

        if options.offline_dir:
            bodies = self._offline_bodies(active)
            self.cache = HttpCache(".cache/offline", enabled=False)
        else:
            bodies = self._fetch(active)

        allowed = [str(p).lower() for p in (self.cfg.get("parsing.protocols") or [])]
        configs: list[VpnConfig] = []
        invalid = 0
        raw_count = 0
        per_source_counts: dict[str, int] = {}

        for source in active:
            body = bodies.get(source.url)
            if body is None:
                source.found = 0
                continue
            decoded = decode_body(
                body, allow_double=bool(self.cfg.get("parsing.allow_double_base64", True))
            )
            # A number of CDN/error pages are returned with HTTP 200. Treat
            # them as failed sources instead of recording a misleading
            # successful fetch with zero usable configs.
            if looks_like_error_page(decoded):
                source.ok = False
                source.error = "source returned an HTML/CDN error page"
                source.found = 0
                per_source_counts[source.name or source.url] = 0
                continue
            chunks = extract_uris(decoded)
            raw_count += len(chunks)
            found = 0
            for chunk in chunks:
                cfg = parse_uri(chunk, source=source.url)
                if cfg is None:
                    invalid += 1
                    continue
                if allowed and cfg.protocol not in allowed:
                    continue
                configs.append(cfg)
                found += 1
            source.found = found
            per_source_counts[source.name or source.url] = found

        # --- source health bookkeeping ---------------------------------
        # A paused source has not been retried in this run. Recording it as
        # another failure would refresh ``last_fail_at`` every hour and make
        # its cool-down never expire, so only record sources we actually ran.
        for source in (active if not options.offline_dir else []):
            health.record(source)

        # Keep one copy of every logical config. When identical entries appear
        # in more than one feed, prefer the source the operator weighted more
        # heavily; health breaks ties. This makes ``weight=`` annotations in
        # links.txt meaningful without ever adding a removed source back.
        source_by_url = {source.url: source for source in sources}

        def source_priority(cfg: VpnConfig) -> tuple[float, float, str]:
            source = source_by_url.get(cfg.source)
            weight = max(0, source.weight) if source else 1
            return (float(weight), health.reliability(cfg.source), cfg.source)

        unique_by_fingerprint: dict[str, VpnConfig] = {}
        unique_order: list[str] = []
        for cfg in configs:
            previous = unique_by_fingerprint.get(cfg.fingerprint)
            if previous is None:
                unique_by_fingerprint[cfg.fingerprint] = cfg
                unique_order.append(cfg.fingerprint)
            elif source_priority(cfg) > source_priority(previous):
                unique_by_fingerprint[cfg.fingerprint] = cfg
        unique = [unique_by_fingerprint[fingerprint] for fingerprint in unique_order]
        duplicates = len(configs) - len(unique)

        # --- geo + security + scoring ----------------------------------
        for cfg in unique:
            detected = geo.detect(cfg.remark)
            cfg.geo_code, cfg.geo_name, cfg.geo_flag = detected.code, detected.name, detected.flag

        kept, audit_report = audit(unique, self.cfg.section("security"))
        scoring.score_all(kept, reliability_of=health.reliability)

        # --- liveness probe --------------------------------------------
        probe_mode = (options.probe or str(self.cfg.get("probe.mode", "off"))).lower()
        probe_summary = probe_configs(
            kept,
            ProbeSettings(
                mode=probe_mode,
                workers=int(self.cfg.get("probe.workers", 96)),
                timeout=float(self.cfg.get("probe.timeout", 4.0)),
                tls=bool(self.cfg.get("probe.tls", False)),
                max_endpoints=int(self.cfg.get("probe.max_endpoints", 12000)),
                cache_ttl=int(self.cfg.get("probe.cache_ttl", 900)),
                state_file=str(self.cfg.get("probe.state_file", "state/probe_cache.json")),
                persist=not options.dry_run,
            ),
            on_progress=lambda done, total: self.log(f"  … probed {done}/{total} endpoints"),
        )
        require_verified = bool(self.cfg.get("probe.require_verified", True)) or bool(
            self.cfg.get("probe.drop_dead", True)
        )
        quality = {
            "require_verified": require_verified,
            "candidates_after_security": len(kept),
            "published_after_probe": len(kept),
            "excluded_unverified": 0,
        }
        if probe_summary.get("mode", "off") != "off":
            # Scores depend on the verdict, so re-score after probing.
            scoring.score_all(kept, reliability_of=health.reliability)
            if require_verified:
                before_filter = len(kept)
                # ``None`` means the endpoint was not in this run's fresh
                # probe set (for example because of max_endpoints). It is not
                # evidence of quality and must never be published in strict
                # mode alongside an explicit failed verdict.
                kept = [cfg for cfg in kept if cfg.verified is True]
                quality["excluded_unverified"] = before_filter - len(kept)
                quality["published_after_probe"] = len(kept)

        # --- sort + limit + name ---------------------------------------
        kept = scoring.sort_configs(kept, str(self.cfg.get("scoring.sort", "score")))
        per_protocol_limit = int(self.cfg.get("limits.per_protocol", 0) or 0)
        if per_protocol_limit:
            buckets: dict[str, int] = {}
            trimmed: list[VpnConfig] = []
            for cfg in kept:
                if buckets.get(cfg.protocol, 0) >= per_protocol_limit:
                    continue
                buckets[cfg.protocol] = buckets.get(cfg.protocol, 0) + 1
                trimmed.append(cfg)
            kept = trimmed
        max_configs = options.limit or int(self.cfg.get("limits.max_configs", 0) or 0)
        if max_configs:
            kept = kept[:max_configs]
        quality["published"] = len(kept)

        uris = naming.apply_names(
            kept,
            template=str(self.cfg.get("naming.template", "{brand} {index}")),
            brand=str(self.cfg.get("profile.brand", "POPVPN")),
            separator=str(self.cfg.get("naming.separator", "|")),
            index_width=int(self.cfg.get("naming.index_width", 4)),
            unknown_label=str(self.cfg.get("geo.unknown_label", "GLOBAL")),
            max_length=int(self.cfg.get("naming.max_length", 60)),
            unique=bool(self.cfg.get("naming.unique", True)),
        )

        by_protocol: dict[str, int] = {}
        for cfg in kept:
            by_protocol[cfg.protocol] = by_protocol.get(cfg.protocol, 0) + 1
        by_country = geo.country_summary(
            [geo.Geo(c.geo_code, c.geo_name, c.geo_flag) for c in kept]
        )

        duration_ms = int((time.monotonic() - started) * 1000)
        sources_summary = {
            "total": len(sources),
            "ok": sum(1 for s in active if s.ok),
            "failed": sum(1 for s in active if not s.ok),
            "paused": len(paused),
        }

        history_path = self.cfg.get("outputs.history_file", "state/history.json")
        history = load_history(history_path, int(self.cfg.get("outputs.history_keep", 240)))
        previous_total = history[-1]["total"] if history else None

        stats: dict = {
            "generated_at": _utc_now(),
            "version": __version__,
            "duration_ms": duration_ms,
            "total": len(kept),
            "unique": len(unique),
            "parsed": len(configs),
            "raw_lines": raw_count,
            "duplicates": duplicates,
            "invalid": invalid,
            "by_protocol": by_protocol,
            "by_country": by_country,
            "country_count": len([row for row in by_country if row["code"]]),
            "sources": sources_summary,
            "source_list": [
                {
                    "name": s.name,
                    "url": s.url,
                    "last_configs": s.found,
                    "ok": s.ok,
                    "from_cache": s.from_cache,
                    "elapsed_ms": s.elapsed_ms,
                    "error": s.error,
                    "success_rate": round(health.reliability(s.url), 3),
                    "paused": health.is_paused(s.url) or not s.enabled,
                }
                for s in sources
            ],
            "per_source": per_source_counts,
            "cache": self.cache.stats(),
            "probe": probe_summary,
            "quality": quality,
            "audit": audit_report.as_dict(),
            "previous_total": previous_total,
            "history": history,
        }

        profile = self.cfg.section("profile")
        profile["generated_at"] = stats["generated_at"]
        repo = str(self.cfg.get("profile.repo", "") or "")
        branch = str(self.cfg.get("profile.branch", "main") or "main")
        base = f"https://raw.githubusercontent.com/{repo}/{branch}" if repo else ""

        # Do not publish an empty snapshot solely because the network or every
        # upstream source failed. Keeping the last successful verified output
        # is safer than atomically replacing it with an outage page. A genuine
        # successful-but-empty feed still proceeds and is written normally.
        all_active_sources_failed = bool(active) and not any(source.ok for source in active)
        if all_active_sources_failed and not options.dry_run:
            health.save()
            self.log("[popvpn] every active source failed; existing outputs were left untouched")
            return {
                "ok": False,
                "dry_run": False,
                "reason": "every active source failed",
                "stats": stats,
                "uris": uris,
                "written": {},
                "log": self.log_lines,
            }

        if options.dry_run:
            self.log(
                f"[popvpn] dry-run: {len(kept)} configs, {duplicates} duplicates removed, "
                f"{invalid} invalid lines, {duration_ms} ms"
            )
            return {
                "ok": True,
                "dry_run": True,
                "stats": stats,
                "uris": uris,
                "written": {},
                "log": self.log_lines,
            }

        written = self._write(
            kept,
            uris,
            stats,
            profile,
            history,
            history_path,
            health,
            protocols=allowed,
            base=base,
        )

        if options.notify_enabled and bool(self.cfg.get("notify.enabled", True)):
            notification = notify(stats, self.http_settings if not options.offline_dir else None)
            if notification.get("sent") or notification.get("reason"):
                self.log(
                    f"[popvpn] notification ({notification.get('provider') or 'none'}): "
                    f"{notification.get('reason') or 'sent'} {notification.get('error') or ''}".strip()
                )
            stats["notification"] = notification

        health.save()
        self.log(
            f"[popvpn] done · {len(kept)} configs · {len(written)} files · "
            f"{written_bytes(written):,} bytes · {duration_ms} ms"
        )
        return {
            "ok": True,
            "dry_run": False,
            "stats": stats,
            "uris": uris,
            "written": written,
            "log": self.log_lines,
        }

    # -- outputs ---------------------------------------------------------
    def _write(
        self,
        configs: list[VpnConfig],
        uris: list[str],
        stats: dict,
        profile: dict,
        history: list[dict],
        history_path: str,
        health: SourceHealth,
        *,
        protocols: list[str],
        base: str,
    ) -> dict:
        options = self.options
        out_dir = Path(options.outputs_dir or str(self.cfg.get("outputs.dir", "outputs")))
        sink = writers.Written()
        limits = self.cfg.section("limits")
        best_count = int(limits.get("best_count", 100))
        clash_max = int(limits.get("clash_max", 3000))

        plain = writers.plain_subscription(uris, profile)
        encoded = writers.base64_subscription(uris)

        if bool(self.cfg.get("outputs.root_files", True)):
            sink.add(Path("working_configs.txt"), plain)
            sink.add(Path("base64.txt"), encoded)
            sink.add(Path("stats.txt"), render_stats_txt(stats, profile))

        sink.add(out_dir / "all.txt", plain)
        sink.add(out_dir / "all_base64.txt", encoded)

        if bool(self.cfg.get("outputs.by_protocol", True)):
            # Keep URLs stable for the protocols enabled in config.yaml.  A
            # quiet feed may have no TUIC / WireGuard node in one particular
            # run, but users should receive an empty, valid subscription
            # instead of a 404 from a documented URL.
            groups = writers.group_by_protocol(configs, uris)
            for protocol in dict.fromkeys(protocols):
                group = groups.get(protocol, [])
                sink.add(
                    out_dir / "by-protocol" / f"{protocol}.txt",
                    writers.plain_subscription(group, profile),
                )
                sink.add(
                    out_dir / "by-protocol" / f"{protocol}_base64.txt",
                    writers.base64_subscription(group),
                )

        if bool(self.cfg.get("outputs.by_country", True)):
            for country, group in writers.group_by_country(configs, uris).items():
                sink.add(
                    out_dir / "by-country" / f"{country.lower()}.txt",
                    writers.plain_subscription(group, profile),
                )

        # Write these on every run, including an empty but valid subscription,
        # so a formerly good node can never survive in a stale best-list.
        best_uris = uris[:best_count] if best_count > 0 else []
        sink.add(
            out_dir / "best.txt",
            writers.plain_subscription(best_uris, profile),
        )
        sink.add(
            out_dir / "best_base64.txt",
            writers.base64_subscription(best_uris),
        )

        # The verified subscription is a usability promise: never replace a
        # known-good snapshot with an empty file merely because a probe was
        # intentionally disabled or this run produced no live endpoint. It is
        # rotated only after at least one fresh successful verdict. This is
        # independent from the strict all-output policy above, which can still
        # intentionally become empty when no current config qualifies.
        verified = [(cfg, uri) for cfg, uri in zip(configs, uris) if cfg.verified is True]
        verified_uris = [uri for _, uri in verified]
        verified_path = out_dir / "verified.txt"
        verified_base64_path = out_dir / "verified_base64.txt"
        probe_active = stats.get("probe", {}).get("mode", "off") != "off"
        preserve_verified = bool(self.cfg.get("outputs.preserve_verified_on_empty", True))
        have_previous_verified = verified_path.exists() and verified_base64_path.exists()
        keep_previous_verified = (
            preserve_verified and have_previous_verified and (not probe_active or not verified_uris)
        )
        stats.setdefault("quality", {})["verified_output_preserved"] = keep_previous_verified
        if keep_previous_verified:
            self.log("[popvpn] kept the previous verified snapshot (no new live verdict)")
        else:
            sink.add(verified_path, writers.plain_subscription(verified_uris, profile))
            sink.add(verified_base64_path, writers.base64_subscription(verified_uris))

        # Empty documents are safer than leaving a previous run's proxies in
        # place when no endpoint passes the current quality gate.
        if bool(self.cfg.get("outputs.clash", True)):
            sink.add(out_dir / "clash.yaml", writers.clash_document(configs[:clash_max], profile))
        if bool(self.cfg.get("outputs.singbox", True)):
            sink.add(out_dir / "singbox.json", writers.singbox_document(configs[:clash_max], profile))

        stats_payload = dict(stats)
        stats_payload.pop("history", None)
        sink.add(out_dir / "stats.json", json.dumps(stats_payload, ensure_ascii=False, indent=2) + "\n")
        sink.add(
            out_dir / "sources.json",
            json.dumps(health.summary(), ensure_ascii=False, indent=2) + "\n",
        )

        # --- history + sparkline ---------------------------------------
        entry = build_run_entry(stats)
        history = history + [entry]
        if options.keep_history:
            save_history(history_path, history, int(self.cfg.get("outputs.history_keep", 240)))
            sink.files[str(history_path)] = Path(history_path).stat().st_size
        stats["history"] = history
        values = [run.get("total", 0) for run in history]
        spark_path = Path(self.cfg.get("outputs.sparkline", "outputs/history.svg"))
        sink.add(spark_path, sparkline_svg(values, label="configs"))

        # --- README + dashboard ----------------------------------------
        markdown = render_markdown(stats, repo=str(profile.get("repo", "")), branch=str(profile.get("branch", "main")))
        if (
            options.write_readme
            and self.cfg.get("outputs.readme", "")
            and inject_readme(self.cfg.get("outputs.readme", "README.md"), markdown)
        ):
            self.log("[popvpn] README statistics block updated")
        sink.add(out_dir / "SUMMARY.md", markdown)

        dashboard_dir = str(self.cfg.get("outputs.dashboard", "dashboard"))
        if dashboard_dir:
            from .dashboard import build_dashboard_data, write_dashboard

            links = {}
            if base:
                links = {
                    "plain": f"{base}/working_configs.txt",
                    "base64": f"{base}/base64.txt",
                    "clash": f"{base}/outputs/clash.yaml",
                    "sing-box": f"{base}/outputs/singbox.json",
                    "best": f"{base}/outputs/best.txt",
                    "verified": f"{base}/outputs/verified.txt",
                    "stats": f"{base}/stats.txt",
                    "sources": f"{base}/outputs/sources.json",
                }
            data = build_dashboard_data(
                stats=stats,
                configs=configs,
                max_configs=int(limits.get("dashboard_configs", 400)),
                links=links,
            )
            for path, size in write_dashboard(dashboard_dir, data, history_values=values).items():
                sink.files[path] = size

        # Country and protocol folders are entirely generated. Reconcile them
        # so files for a node/country that no longer passed today's checks do
        # not remain publicly reachable from a prior run.
        expected = {Path(path) for path in sink.files}
        for directory in (out_dir / "by-country", out_dir / "by-protocol"):
            if not directory.exists():
                continue
            for stale in directory.glob("*.txt"):
                if stale not in expected:
                    try:
                        stale.unlink()
                    except OSError:  # pragma: no cover - best effort on read-only filesystems
                        self.log(f"[popvpn] could not remove stale output: {stale}")

        return sink.files


def written_bytes(written: dict) -> int:
    return sum(int(size) for size in written.values())


def run(options: Options | None = None) -> dict:
    return Pipeline(options).run()
