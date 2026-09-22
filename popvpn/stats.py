"""Statistics, run history and the README/GitHub-Summary renderers."""

from __future__ import annotations

import json
import time
from pathlib import Path

from .protocols import Config

HISTORY_MARKERS = ("<!-- POPVPN:STATS:START -->", "<!-- POPVPN:STATS:END -->")


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def load_history(path: str | Path, keep: int = 240) -> list[dict]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    runs = data.get("runs") if isinstance(data, dict) else data
    if not isinstance(runs, list):
        return []
    return runs[-keep:]


def save_history(path: str | Path, runs: list[dict], keep: int = 240) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    runs = runs[-keep:]
    file_path.write_text(
        json.dumps({"updated_at": int(time.time()), "runs": runs}, indent=1),
        encoding="utf-8",
    )


def delta(current: int, previous: int | None) -> str:
    if previous is None:
        return ""
    diff = current - previous
    if diff == 0:
        return "±0"
    return f"+{diff}" if diff > 0 else str(diff)


# ---------------------------------------------------------------------------
# Sparkline
# ---------------------------------------------------------------------------


def sparkline_svg(
    values: list[int],
    *,
    width: int = 720,
    height: int = 120,
    stroke: str = "#7c3aed",
    fill: str = "#7c3aed33",
    label: str = "",
) -> str:
    """Tiny dependency-free SVG line chart used in the README/dashboard."""

    values = [int(v) for v in values]
    if not values:
        values = [0]
    if len(values) == 1:
        values = values * 2
    top = max(values) or 1
    bottom = min(values)
    span = (top - bottom) or 1
    step_x = width / max(1, (len(values) - 1))
    points = []
    for index, value in enumerate(values):
        x = index * step_x
        y = height - ((value - bottom) / span) * (height - 16) - 8
        points.append(f"{x:.1f},{y:.1f}")
    line = " ".join(points)
    area = f"0,{height} {line} {width},{height}"
    last = values[-1]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="{label or 'history'}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{stroke}" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="{stroke}" stop-opacity="0.02"/>
    </linearGradient>
  </defs>
  <polygon points="{area}" fill="{fill.replace('33', '')}" opacity="0.25"/>
  <polygon points="{area}" fill="url(#g)"/>
  <polyline points="{line}" fill="none" stroke="{stroke}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
  <circle cx="{(len(values) - 1) * step_x:.1f}" cy="{points[-1].split(',')[1]}" r="4" fill="{stroke}"/>
  <text x="8" y="18" font-family="monospace" font-size="12" fill="{stroke}">{label} {last}</text>
</svg>
"""


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_stats_txt(stats: dict, profile: dict | None = None) -> str:
    """``stats.txt`` — the human readable summary kept for compatibility."""

    profile = profile or {}
    counts = stats.get("by_protocol", {})
    lines = [
        "=" * 62,
        f"  {profile.get('title', 'POPVPN X')} — subscription statistics",
        "=" * 62,
        f"  generated      : {stats.get('generated_at', '')}",
        f"  run duration   : {stats.get('duration_ms', 0)} ms",
        f"  total configs  : {stats.get('total', 0)}",
        f"  unique configs : {stats.get('unique', 0)}",
        f"  duplicates     : {stats.get('duplicates', 0)}",
        f"  invalid lines  : {stats.get('invalid', 0)}",
        "",
        "  per protocol:",
    ]
    for protocol, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"    {protocol.upper():<12} {count}")
    lines += [
        "",
        f"  countries      : {stats.get('country_count', 0)}",
        "  top countries :",
    ]
    for row in stats.get("by_country", [])[:8]:
        lines.append(
            f"    {row['flag']} {row['code'] or '--'} {row['name']:<20} {row['count']}"
        )
    sources = stats.get("sources", {})
    lines += [
        "",
        f"  sources        : {sources.get('total', 0)} "
        f"(ok {sources.get('ok', 0)} / failed {sources.get('failed', 0)} / paused {sources.get('paused', 0)})",
        f"  cache hit rate : {stats.get('cache', {}).get('hit_rate', 0):.0%}",
    ]
    probe = stats.get("probe", {})
    if probe.get("mode", "off") != "off":
        lines += [
            "",
            f"  probe ({probe.get('mode')}):",
            f"    endpoints    : {probe.get('endpoints_total', 0)}",
            f"    alive        : {probe.get('alive', 0)}",
            f"    dead         : {probe.get('dead', 0)}",
            f"    avg latency  : {probe.get('avg_latency_ms', 0)} ms",
        ]
    audit = stats.get("audit", {})
    lines += [
        "",
        "  security audit :",
        f"    insecure        : {audit.get('insecure', 0)}",
        f"    private hosts   : {audit.get('private_hosts', 0)}",
        f"    placeholder keys: {audit.get('placeholder_credentials', 0)}",
        f"    dropped         : {audit.get('dropped', 0)}",
        "",
        "=" * 62,
        "",
    ]
    return "\n".join(lines)


def _country_output_name(code: object) -> str:
    """Return the stable filename used for one country subscription."""

    normalized = str(code or "").upper()
    return normalized.lower() if len(normalized) == 2 and normalized.isalpha() else "global"


def render_markdown(stats: dict, *, repo: str = "", branch: str = "main", title: str = "POPVPN X") -> str:
    """Render the live README block, including copyable country feed URLs."""

    base = f"https://raw.githubusercontent.com/{repo}/{branch}" if repo else ""
    counts = stats.get("by_protocol", {})
    sources = stats.get("sources", {})
    probe = stats.get("probe", {})
    previous = stats.get("previous_total")
    countries = stats.get("by_country", [])

    badges = [
        f"![Total](https://img.shields.io/badge/CONFIGS-{stats.get('total', 0):,}-7c3aed?style=flat-square)",
        f"![VLESS](https://img.shields.io/badge/VLESS-{counts.get('vless', 0):,}-8b5cf6?style=flat-square)",
        f"![VMess](https://img.shields.io/badge/VMess-{counts.get('vmess', 0):,}-3b82f6?style=flat-square)",
        f"![Trojan](https://img.shields.io/badge/Trojan-{counts.get('trojan', 0):,}-f97316?style=flat-square)",
        f"![SS](https://img.shields.io/badge/Shadowsocks-{counts.get('ss', 0):,}-22c55e?style=flat-square)",
        f"![Sources](https://img.shields.io/badge/SOURCES-{sources.get('ok', 0)}%2F{sources.get('total', 0)}-06b6d4?style=flat-square)",
    ]
    if stats.get("country_count", 0):
        badges.append(
            f"![Countries](https://img.shields.io/badge/COUNTRIES-{stats.get('country_count', 0)}-eab308?style=flat-square)"
        )
    if probe.get("alive"):
        badges.append(
            f"![Verified](https://img.shields.io/badge/ALIVE-{probe.get('alive', 0):,}-16a34a?style=flat-square)"
        )

    lines = [
        " | ".join(badges),
        "",
        f"**Last update:** `{stats.get('generated_at', '')}` · "
        f"**{stats.get('total', 0):,} configs**",
    ]
    if previous is not None:
        lines[-1] += f" ({delta(stats.get('total', 0), previous)} vs previous run)"
    lines += [
        "",
        "| Protocol | Configs | Share |",
        "| --- | ---: | ---: |",
    ]
    total = max(1, stats.get("total", 1))
    for protocol, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {protocol.upper()} | {count:,} | {count / total:.1%} |")
    lines += [
        "",
        "| Top countries | Configs |",
        "| --- | ---: |",
    ]
    for row in countries[:8]:
        code = str(row.get("code", ""))
        label = f"{row.get('flag', '')} {row.get('name', 'Unknown')}"
        if code in ("", "?"):
            label = "🏳️ GLOBAL / Unknown"
        lines.append(f"| {label.strip()} | {int(row.get('count', 0)):,} |")
    lines += [
        "",
        "<details><summary><b>Pipeline health</b></summary>",
        "",
        f"- sources: **{sources.get('ok', 0)}/{sources.get('total', 0)}** ok, "
        f"{sources.get('failed', 0)} failed, {sources.get('paused', 0)} auto-paused",
        f"- duplicates removed: **{stats.get('duplicates', 0):,}**",
        f"- invalid lines skipped: **{stats.get('invalid', 0):,}**",
        f"- HTTP cache hit rate: **{stats.get('cache', {}).get('hit_rate', 0):.0%}**",
        f"- security flags: **{stats.get('audit', {}).get('insecure', 0)}** insecure, "
        f"**{stats.get('audit', {}).get('private_hosts', 0)}** private hosts",
    ]
    if probe.get("mode", "off") != "off":
        lines.append(
            f"- liveness probe ({probe.get('mode')}): **{probe.get('alive', 0):,}** endpoints alive, "
            f"{probe.get('dead', 0):,} dead, avg {probe.get('avg_latency_ms', 0)} ms"
        )
    lines += [
        f"- run duration: **{stats.get('duration_ms', 0)} ms**",
        "",
        "</details>",
    ]
    if base:
        lines += [
            "",
            "**Subscription:** "
            f"[plain]({base}/working_configs.txt) · "
            f"[base64]({base}/base64.txt) · "
            f"[all]({base}/outputs/all.txt) · "
            f"[best]({base}/outputs/best.txt) · "
            f"[verified]({base}/outputs/verified.txt) · "
            f"[clash]({base}/outputs/clash.yaml) · "
            f"[sing-box]({base}/outputs/singbox.json) · "
            f"[stats]({base}/stats.txt)",
            "",
            "<details><summary><b>🌍 همهٔ لینک‌های کشورها در آخرین اجرا — Copyable</b></summary>",
            "",
            "```text",
        ]
        for row in countries:
            code = str(row.get("code", ""))
            name = str(row.get("name", "Unknown"))
            flag = str(row.get("flag", "🏳️"))
            count = int(row.get("count", 0))
            filename = _country_output_name(code)
            label = "GLOBAL / Unknown" if filename == "global" else name
            lines.append(f"{flag} {label} ({count:,}): {base}/outputs/by-country/{filename}.txt")
        lines += ["```", "", "</details>"]
    return "\n".join(lines) + "\n"

def inject_readme(readme_path: str | Path, block: str) -> bool:
    """Replace the content between the stats markers in ``README.md``."""

    path = Path(readme_path)
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    start, end = HISTORY_MARKERS
    if start not in text or end not in text:
        return False
    head, _, rest = text.partition(start)
    _, _, tail = rest.partition(end)
    updated = f"{head}{start}\n\n{block.strip()}\n\n{end}{tail}"
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def build_run_entry(stats: dict) -> dict:
    """Compact history record (kept small so the file stays diff-friendly)."""

    return {
        "at": int(time.time()),
        "total": int(stats.get("total", 0)),
        "by_protocol": {k: int(v) for k, v in stats.get("by_protocol", {}).items()},
        "sources_ok": int(stats.get("sources", {}).get("ok", 0)),
        "sources_total": int(stats.get("sources", {}).get("total", 0)),
        "alive": int(stats.get("probe", {}).get("alive", 0)),
        "countries": int(stats.get("country_count", 0)),
        "duration_ms": int(stats.get("duration_ms", 0)),
    }


def load_configs(path: str | Path) -> list[Config]:  # pragma: no cover - convenience
    """Reload configs from a ``stats.json`` dump (used by the dashboard CLI)."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Config(**item) for item in data.get("configs", [])]
