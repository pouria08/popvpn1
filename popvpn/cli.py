"""Command line interface.

    python main.py                       # full run (writes outputs/)
    python main.py --dry-run             # fetch + parse, write nothing
    python main.py --offline tests/data  # run against local files (no network)
    python main.py check-source URL      # diagnose a single subscription URL
    python main.py parse file.txt        # parse a local file, print a summary
    python main.py sources               # show per-source health
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import Config, ConfigError
from .pipeline import Options, Pipeline
from .protocols import decode_body, extract_uris, parse_uri
from .sources import SourceHealth, load_sources

SUBCOMMANDS = ("update", "check-source", "parse", "sources", "version")


def build_parser() -> argparse.ArgumentParser:
    """Parser for the ``update`` command (the default one)."""

    parser = argparse.ArgumentParser(
        prog="popvpn",
        description="POPVPN X — self-updating VPN subscription pipeline",
    )
    parser.add_argument("--version", action="version", version=f"popvpn {__version__}")

    group = parser.add_argument_group("update options")
    group.add_argument("--config", default="config.yaml", help="path to config.yaml")
    group.add_argument("--dry-run", action="store_true", help="fetch and parse, write nothing")
    group.add_argument("--limit", type=int, default=0, help="cap the number of published configs")
    group.add_argument("--probe", default="", choices=["", "off", "tcp", "tls"], help="liveness probe mode")
    group.add_argument("--workers", type=int, default=0, help="concurrent downloads")
    group.add_argument("--source", action="append", default=[], help="extra/override source URL")
    group.add_argument("--offline", default="", metavar="DIR", help="read files from DIR instead of the network")
    group.add_argument("--outputs-dir", default="", help="override outputs directory")
    group.add_argument("--no-cache", action="store_true", help="ignore the HTTP cache")
    group.add_argument("--no-history", action="store_true", help="do not append to the run history")
    group.add_argument("--no-readme", action="store_true", help="do not touch README.md")
    group.add_argument("--no-notify", action="store_true", help="never send notifications")
    group.add_argument("--sample", type=int, default=0, help="print the first N generated URIs")
    group.add_argument("--json", action="store_true", help="print a machine readable summary")
    group.add_argument("--quiet", action="store_true", help="only print the final summary")
    parser.add_argument("--verbose", action="store_true", help="extra logging")
    return parser


def build_target_parser(description: str, metavar: str) -> argparse.ArgumentParser:
    """Parser for the ``parse`` / ``check-source`` commands."""

    parser = argparse.ArgumentParser(prog="popvpn", description=description)
    parser.add_argument("--config", default="config.yaml", help="path to config.yaml")
    parser.add_argument("targets", nargs="*", metavar=metavar)
    return parser


def _split_command(argv: list[str]) -> tuple[str, list[str]]:
    """``popvpn parse a.txt`` and ``popvpn --dry-run`` are both valid."""

    if argv and argv[0] in SUBCOMMANDS:
        return argv[0], argv[1:]
    return "update", argv


def _options_from_args(parsed: argparse.Namespace) -> Options:
    return Options(
        config_path=parsed.config,
        dry_run=parsed.dry_run,
        limit=parsed.limit,
        probe=parsed.probe,
        workers=parsed.workers,
        sources=parsed.source,
        offline_dir=parsed.offline,
        outputs_dir=parsed.outputs_dir,
        no_cache=parsed.no_cache,
        keep_history=not parsed.no_history,
        write_readme=not parsed.no_readme,
        notify_enabled=not parsed.no_notify,
        verbose=parsed.verbose,
        quiet=parsed.quiet,
    )


def _cmd_update(parsed: argparse.Namespace) -> int:
    options = _options_from_args(parsed)
    pipeline = Pipeline(options)
    result = pipeline.run()
    stats = result.get("stats", {})

    if parsed.sample:
        for uri in result.get("uris", [])[: parsed.sample]:
            print(uri)

    if parsed.json:
        print(
            json.dumps(
                {
                    "total": stats.get("total", 0),
                    "unique": stats.get("unique", 0),
                    "duplicates": stats.get("duplicates", 0),
                    "invalid": stats.get("invalid", 0),
                    "by_protocol": stats.get("by_protocol", {}),
                    "sources": stats.get("sources", {}),
                    "probe": stats.get("probe", {}),
                    "duration_ms": stats.get("duration_ms", 0),
                    "files": sorted(result.get("written", {})),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    counts = stats.get("by_protocol", {})
    print(
        "[popvpn] "
        f"total={stats.get('total', 0)} unique={stats.get('unique', 0)} "
        f"dupes={stats.get('duplicates', 0)} invalid={stats.get('invalid', 0)} "
        + " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    )
    if result.get("written"):
        print(f"[popvpn] wrote {len(result['written'])} files")
    return 0


def _cmd_check_source(parsed: argparse.Namespace) -> int:
    from .http import HttpSettings, fetch

    urls = parsed.targets
    if not urls:
        print("usage: popvpn check-source URL [URL ...]", file=sys.stderr)
        return 2
    settings = HttpSettings()
    exit_code = 0
    for url in urls:
        result = fetch(url, settings)
        print(f"\n{url}")
        if not result.ok:
            print(f"  FAILED: {result.error} (status {result.status})")
            exit_code = 1
            continue
        body = decode_body(result.text)
        chunks = extract_uris(body)
        configs = [cfg for cfg in (parse_uri(chunk) for chunk in chunks) if cfg]
        protocols: dict[str, int] = {}
        for cfg in configs:
            protocols[cfg.protocol] = protocols.get(cfg.protocol, 0) + 1
        print(f"  status={result.status} bytes={result.size} ms={result.elapsed_ms}")
        print(f"  uris={len(chunks)} parsed={len(configs)} invalid={len(chunks) - len(configs)}")
        print("  protocols: " + (", ".join(f"{k}={v}" for k, v in sorted(protocols.items())) or "-"))
        if configs:
            print(f"  sample: {configs[0].name or configs[0].remark or configs[0].host}")
        if not configs:
            exit_code = 1
    return exit_code


def _cmd_parse(parsed: argparse.Namespace) -> int:
    paths = parsed.targets
    if not paths:
        print("usage: popvpn parse FILE [FILE ...]", file=sys.stderr)
        return 2
    total = invalid = 0
    protocols: dict[str, int] = {}
    for path in paths:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        chunks = extract_uris(decode_body(text))
        parsed_configs = [cfg for cfg in (parse_uri(chunk) for chunk in chunks) if cfg]
        total += len(parsed_configs)
        invalid += len(chunks) - len(parsed_configs)
        for cfg in parsed_configs:
            protocols[cfg.protocol] = protocols.get(cfg.protocol, 0) + 1
    payload = {"total": total, "invalid": invalid, "by_protocol": protocols}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _cmd_sources(parsed: argparse.Namespace) -> int:
    config = Config.load(parsed.config)
    health = SourceHealth(
        config.get("sources.state_file", "state/sources.json"),
        max_failures=int(config.get("sources.max_failures", 3)),
        revive_after_hours=float(config.get("sources.revive_after_hours", 6)),
    )
    sources = load_sources(config.get("sources.file", "links.txt"))
    print(f"{'STATE':<8} {'CONFIGS':>8} {'RELIAB':>7}  SOURCE")
    for source in sources:
        record = health.records.get(source.url, {})
        state = "paused" if health.is_paused(source.url) else ("ok" if record.get("last_configs") else "new")
        if not source.enabled:
            state = "off"
        print(
            f"{state:<8} {int(record.get('last_configs', 0)):>8} "
            f"{float(record.get('reliability', 1.0)):>7.2f}  {source.name}  {source.url}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    command, rest = _split_command(argv)
    try:
        if command == "version":
            print(f"popvpn {__version__}")
            return 0
        if command == "check-source":
            parsed = build_target_parser(
                "Diagnose one or more subscription URLs", "URL"
            ).parse_args(rest)
            return _cmd_check_source(parsed)
        if command == "parse":
            parsed = build_target_parser("Parse local subscription files", "FILE").parse_args(rest)
            return _cmd_parse(parsed)
        if command == "sources":
            parsed = build_parser().parse_args(rest)
            return _cmd_sources(parsed)
        parsed = build_parser().parse_args(rest)
        return _cmd_update(parsed)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"missing file: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:  # pragma: no cover - interactive
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
