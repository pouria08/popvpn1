from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from popvpn.pipeline import Options, run

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tests" / "data"
CONFIG = ROOT / "config.yaml"

EXPECTED_FILES = [
    "working_configs.txt",
    "base64.txt",
    "stats.txt",
    "outputs/all.txt",
    "outputs/all_base64.txt",
    "outputs/best.txt",
    "outputs/best_base64.txt",
    "outputs/stats.json",
    "outputs/sources.json",
    "outputs/history.svg",
    "outputs/clash.yaml",
    "outputs/singbox.json",
    "outputs/SUMMARY.md",
    "outputs/by-protocol/vless.txt",
    "outputs/by-protocol/vmess.txt",
    "outputs/by-protocol/trojan.txt",
    "outputs/by-protocol/ss.txt",
    "outputs/by-country/de.txt",
    "outputs/by-country/nl.txt",
    "dashboard/index.html",
    "dashboard/data.json",
    "dashboard/history.svg",
    "state/history.json",
]


def _options(**overrides) -> Options:
    options = dict(
        config_path=str(CONFIG),
        offline_dir=str(DATA),
        keep_history=True,
        write_readme=True,
        notify_enabled=False,
        quiet=True,
    )
    options.update(overrides)
    return Options(**options)


@pytest.fixture()
def result(workspace):
    return run(_options())


def test_pipeline_reports_counts(result):
    stats = result["stats"]
    assert result["ok"] is True
    # the fixtures contain 13 distinct configs published across 3 files
    assert stats["total"] == 13
    assert stats["unique"] == 13
    assert stats["parsed"] == 27
    assert stats["duplicates"] == 14         # padded, HTML-escaped, concatenated + repeated files
    assert stats["invalid"] == 2             # the two deliberately broken lines
    assert stats["by_protocol"] == {
        "vless": 3, "vmess": 3, "ss": 3, "trojan": 1, "tuic": 1, "hy2": 1, "wireguard": 1,
    }
    assert stats["country_count"] >= 8


def test_pipeline_writes_every_artefact(result, workspace):
    written = result["written"]
    for name in EXPECTED_FILES:
        assert Path(name).exists(), f"missing {name}"
        assert any(path.endswith(name) for path in written), f"{name} not reported"


def test_plain_and_base64_outputs_match(result):
    plain = Path("working_configs.txt").read_text(encoding="utf-8")
    encoded = Path("base64.txt").read_text(encoding="utf-8").strip()
    decoded = base64.b64decode(encoded).decode("utf-8")
    configs_in_plain = [line for line in plain.splitlines() if "://" in line]
    assert configs_in_plain == decoded.splitlines()
    assert plain.startswith("#profile-title: POPVPN X")


def test_names_are_applied_to_uris(result):
    plain = Path("working_configs.txt").read_text(encoding="utf-8")
    assert "#POPVPN 0001" in plain


def test_best_and_per_protocol_splits(result):
    best = Path("outputs/best.txt").read_text(encoding="utf-8")
    vless = Path("outputs/by-protocol/vless.txt").read_text(encoding="utf-8")
    assert "vless://" in best
    assert "vless://" in vless
    assert "trojan://" not in vless


def test_stats_json_is_valid(result):
    payload = json.loads(Path("outputs/stats.json").read_text(encoding="utf-8"))
    assert payload["total"] == result["stats"]["total"]
    assert payload["sources"]["total"] >= 1
    assert "by_protocol" in payload


def test_dashboard_data_has_no_secrets(result):
    data = json.loads(Path("dashboard/data.json").read_text(encoding="utf-8"))
    assert data["total"] == result["stats"]["total"]
    assert data["configs"], "dashboard should list a sample of configs"
    blob = json.dumps(data)
    assert "a1b2c3d4-e5f6-4789-abcd-ef0123456789" not in blob
    assert "sspassword123" not in blob
    # full config URIs must never leak into the public dashboard
    for scheme in ("vless://", "vmess://", "trojan://", "ss://", "tuic://", "hy2://", "wireguard://"):
        assert scheme not in blob
    assert data["links"]["plain"].startswith("https://raw.githubusercontent.com/pouria08/popvpn1/")


def test_dashboard_html_is_self_contained(result):
    html = Path("dashboard/index.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "cdn" not in html.lower() or "example.com" in html
    assert 'fetch("data.json"' in html


def test_readme_block_is_updated(result, workspace):
    text = Path("README.md").read_text(encoding="utf-8")
    assert "<!-- POPVPN:STATS:START -->" in text
    assert "CONFIGS-" in text
    assert "old" not in text
    assert text.endswith("tail\n")


def test_history_grows_and_delta_is_reported(workspace):
    first = run(_options())
    assert first["stats"]["previous_total"] is None
    second = run(_options())
    assert second["stats"]["previous_total"] == first["stats"]["total"]
    history = json.loads(Path("state/history.json").read_text(encoding="utf-8"))
    assert len(history["runs"]) == 2


def test_dry_run_writes_nothing(workspace):
    before = {path.name for path in Path(".").iterdir()}
    result = run(_options(dry_run=True))
    after = {path.name for path in Path(".").iterdir()}
    assert result["dry_run"] is True
    assert result["written"] == {}
    assert before == after
    assert result["uris"], "dry-run should still return the generated URIs"


def test_limit_and_per_protocol_caps(workspace):
    result = run(_options(limit=5))
    assert result["stats"]["total"] == 5
    assert len(result["uris"]) == 5


def test_custom_outputs_dir(workspace):
    result = run(_options(outputs_dir="custom"))
    assert Path("custom/all.txt").exists()
    assert any(path.endswith("custom/all.txt") for path in result["written"])


def test_probe_mode_marks_unreachable_endpoints(workspace, tmp_path):
    # Uses a local, guaranteed-unreachable endpoint so the test never
    # touches the network.
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "local.txt").write_text(
        "vless://a1b2c3d4-e5f6-4789-abcd-ef0123456789@127.0.0.1:9"
        "?security=none&type=tcp#LOCAL\n",
        encoding="utf-8",
    )
    result = run(_options(offline_dir=str(input_dir), probe="tcp"))
    probe = result["stats"]["probe"]
    assert probe["mode"] == "tcp"
    assert probe["endpoints_total"] == 1
    assert probe["dead"] == 1
    assert probe["configs_dead"] == 1
    cache = json.loads(Path("state/probe_cache.json").read_text(encoding="utf-8"))
    assert cache["endpoints"]["127.0.0.1:9"]["ok"] is False
    # second run reuses the cached verdict
    again = run(_options(offline_dir=str(input_dir), probe="tcp"))
    assert again["stats"]["probe"]["endpoints_cached"] == 1


def test_probe_drop_dead(workspace, tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "local.txt").write_text(
        "vless://a1b2c3d4-e5f6-4789-abcd-ef0123456789@127.0.0.1:9"
        "?security=none&type=tcp#LOCAL\n",
        encoding="utf-8",
    )
    monkey = {"POPVPN_PROBE_DROP_DEAD": "true"}
    import os

    os.environ.update(monkey)
    try:
        result = run(_options(offline_dir=str(input_dir), probe="tcp"))
    finally:
        for key in monkey:
            os.environ.pop(key, None)
    assert result["stats"]["total"] == 0


def test_missing_source_list_raises(workspace, monkeypatch, tmp_path):
    # run from a directory without links.txt and without --offline
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)
    with pytest.raises(FileNotFoundError):
        run(_options(offline_dir=""))
