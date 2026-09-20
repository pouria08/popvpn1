"""Build the commit message for an auto-update run.

    python scripts/commit_message.py

Reads ``outputs/stats.json`` and prints a single-line subject in the same
style as the original POPVPN so the repository history stays scannable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Artefacts are written relative to the current working directory, so that is
# also where the scripts look for them.
WORKDIR = Path.cwd()


def build_message(stats: dict) -> str:
    counts = stats.get("by_protocol", {})
    parts = [f"{protocol.upper()}: {count}" for protocol, count in sorted(counts.items(), key=lambda kv: -kv[1])]
    sources = stats.get("sources", {})
    probe = stats.get("probe", {})
    subject = (
        f"Auto-Update: Total: {stats.get('total', 0)}"
        + (" | " + " | ".join(parts) if parts else "")
        + f" | Sources: {sources.get('ok', 0)}/{sources.get('total', 0)}"
        + f" | Dupes: {stats.get('duplicates', 0)}"
    )
    if probe.get("mode", "off") != "off":
        subject += f" | Alive: {probe.get('alive', 0)}"
    if len(subject) > 180:
        subject = subject[:177] + "..."
    return subject


def build_body(stats: dict) -> str:
    lines = [
        f"Generated at {stats.get('generated_at', '')} in {stats.get('duration_ms', 0)} ms.",
        "",
        f"- unique configs: {stats.get('unique', 0)}",
        f"- duplicates removed: {stats.get('duplicates', 0)}",
        f"- invalid lines skipped: {stats.get('invalid', 0)}",
        f"- countries detected: {stats.get('country_count', 0)}",
    ]
    audit = stats.get("audit", {})
    lines.append(
        f"- security: {audit.get('insecure', 0)} insecure, "
        f"{audit.get('private_hosts', 0)} private hosts"
    )
    probe = stats.get("probe", {})
    if probe.get("mode", "off") != "off":
        lines.append(
            f"- probe ({probe.get('mode')}): {probe.get('alive', 0)} alive / "
            f"{probe.get('dead', 0)} dead endpoints"
        )
    cache = stats.get("cache", {})
    lines.append(f"- HTTP cache hit rate: {cache.get('hit_rate', 0):.0%}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    stats_path = Path(argv[0]) if argv else WORKDIR / "outputs" / "stats.json"
    if not stats_path.exists():
        print(f"stats file not found: {stats_path}", file=sys.stderr)
        return 1
    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    print(build_message(stats))
    print()
    print(build_body(stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
