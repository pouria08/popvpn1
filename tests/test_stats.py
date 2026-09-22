from __future__ import annotations

import json

from popvpn import stats

STATS = {
    "generated_at": "2026-01-01 00:00:00 UTC",
    "duration_ms": 1234,
    "total": 100,
    "unique": 120,
    "duplicates": 20,
    "invalid": 5,
    "by_protocol": {"vless": 60, "vmess": 30, "trojan": 10},
    "by_country": [
        {"code": "DE", "name": "Germany", "flag": "🇩🇪", "region": "EU", "count": 40},
        {"code": "", "name": "Unknown", "flag": "🏳️", "region": "", "count": 60},
    ],
    "country_count": 1,
    "sources": {"total": 10, "ok": 8, "failed": 2, "paused": 1},
    "cache": {"enabled": True, "hits": 4, "misses": 6, "hit_rate": 0.4},
    "probe": {"mode": "tcp", "endpoints_total": 50, "alive": 30, "dead": 20, "avg_latency_ms": 180},
    "audit": {"kept": 100, "dropped": 3, "insecure": 7, "private_hosts": 2, "placeholder_credentials": 1,
              "warnings": {"allow-insecure": 7}, "dropped_reasons": {"insecure": 3}},
    "previous_total": 110,
    "history": [],
}


def test_render_stats_txt():
    text = stats.render_stats_txt(STATS, {"title": "POPVPN X"})
    assert "POPVPN X" in text
    assert "total configs  : 100" in text
    assert "VLESS" in text and "60" in text
    assert "alive        : 30" in text


def test_render_markdown_contains_counts_and_links():
    block = stats.render_markdown(STATS, repo="owner/repo", branch="main")
    assert "CONFIGS-100" in block
    assert "owner/repo/main" in block
    assert "| VLESS | 60 | 60.0% |" in block
    assert "COUNTRIES-1" in block
    assert "Germany (40): https://raw.githubusercontent.com/owner/repo/main/outputs/by-country/de.txt" in block
    assert "GLOBAL / Unknown (60): https://raw.githubusercontent.com/owner/repo/main/outputs/by-country/global.txt" in block
    assert "-10 vs previous run" in block


def test_render_markdown_without_repo_has_no_links():
    block = stats.render_markdown(STATS, repo="")
    assert "raw.githubusercontent.com" not in block


def test_delta():
    assert stats.delta(100, 90) == "+10"
    assert stats.delta(90, 100) == "-10"
    assert stats.delta(100, 100) == "±0"
    assert stats.delta(100, None) == ""


def test_inject_readme(tmp_path):
    path = tmp_path / "README.md"
    path.write_text(
        "# title\n\n<!-- POPVPN:STATS:START -->\nold\n<!-- POPVPN:STATS:END -->\n\ntail\n",
        encoding="utf-8",
    )
    assert stats.inject_readme(path, "NEW BLOCK") is True
    text = path.read_text(encoding="utf-8")
    assert "NEW BLOCK" in text
    assert "old" not in text
    assert text.endswith("tail\n")
    # idempotent
    assert stats.inject_readme(path, "NEW BLOCK") is False


def test_inject_readme_without_markers_is_noop(tmp_path):
    path = tmp_path / "README.md"
    path.write_text("# no markers here\n", encoding="utf-8")
    assert stats.inject_readme(path, "x") is False


def test_history_round_trip(tmp_path):
    path = tmp_path / "history.json"
    entry = stats.build_run_entry(STATS)
    assert entry["total"] == 100
    assert entry["by_protocol"]["vless"] == 60
    stats.save_history(path, [entry], keep=10)
    loaded = stats.load_history(path)
    assert loaded == [entry]
    stats.save_history(path, loaded + [entry], keep=1)
    assert len(stats.load_history(path)) == 1


def test_history_missing_file(tmp_path):
    assert stats.load_history(tmp_path / "nope.json") == []


def test_history_truncates(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(json.dumps({"runs": [{"total": i} for i in range(500)]}), encoding="utf-8")
    assert len(stats.load_history(path, keep=240)) == 240


def test_sparkline_svg():
    svg = stats.sparkline_svg([10, 20, 15, 40], label="configs")
    assert svg.startswith("<svg")
    assert "polyline" in svg
    assert svg.count(",") >= 3
    assert "configs 40" in svg


def test_sparkline_handles_single_point():
    assert "<svg" in stats.sparkline_svg([5])
    assert "<svg" in stats.sparkline_svg([])
