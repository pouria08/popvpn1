"""Render a Markdown PR comment summarising a pipeline run.

    python scripts/pr_comment.py [path/to/stats.json]

Used by CI so the result of the live run is visible without opening the
job logs (which are not accessible anonymously).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

WORKDIR = Path.cwd()


def build_comment(stats: dict) -> str:
    counts = stats.get("by_protocol", {})
    sources = stats.get("sources", {})
    audit = stats.get("audit", {})
    probe = stats.get("probe", {})
    countries = stats.get("by_country", [])[:8]

    lines = [
        "### ⚡ POPVPN X — live pipeline run",
        "",
        f"**{stats.get('total', 0):,} configs** published in {stats.get('duration_ms', 0)} ms "
        f"(`{stats.get('generated_at', '')}`)",
        "",
        "| پروتکل | تعداد |",
        "| --- | ---: |",
    ]
    for protocol, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {protocol.upper()} | {count:,} |")
    lines += [
        "",
        "| کشور | تعداد |",
        "| --- | ---: |",
    ]
    for row in countries:
        label = f"{row.get('flag', '')} {row.get('name', '')}".strip()
        lines.append(f"| {label} | {row.get('count', 0):,} |")
    lines += [
        "",
        "<details><summary>جزئیات pipeline</summary>",
        "",
        f"- پارس‌شده: **{stats.get('parsed', 0):,}** · یکتا: **{stats.get('unique', 0):,}**",
        f"- تکراری حذف‌شده: **{stats.get('duplicates', 0):,}** · خط نامعتبر: **{stats.get('invalid', 0):,}**",
        f"- منابع: **{sources.get('ok', 0)}/{sources.get('total', 0)}** سالم · "
        f"{sources.get('failed', 0)} خطا · {sources.get('paused', 0)} متوقف",
        f"- کشورها: **{stats.get('country_count', 0)}** · "
        f"کش HTTP: **{stats.get('cache', {}).get('hit_rate', 0):.0%}**",
        f"- ممیزی امنیتی: **{audit.get('insecure', 0)}** ناامن · "
        f"**{audit.get('private_hosts', 0)}** هاست خصوصی · "
        f"**{audit.get('dropped', 0)}** حذف‌شده",
    ]
    if probe.get("mode", "off") != "off":
        lines.append(
            f"- probe ({probe.get('mode')}): **{probe.get('alive', 0):,}** زنده · "
            f"{probe.get('dead', 0):,} مرده · میانگین {probe.get('avg_latency_ms', 0)} ms"
        )
    lines += ["", "</details>", "", "_خروجی‌ها با `scripts/verify_outputs.py` اعتبارسنجی شدند._"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    stats_path = Path(argv[0]) if argv else WORKDIR / "outputs" / "stats.json"
    if not stats_path.exists():
        print(f"stats file not found: {stats_path}", file=sys.stderr)
        return 1
    print(build_comment(json.loads(stats_path.read_text(encoding="utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
