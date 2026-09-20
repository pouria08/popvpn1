from __future__ import annotations

import json
from pathlib import Path

from popvpn.cli import build_parser, main

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tests" / "data"
CONFIG = str(ROOT / "config.yaml")


def test_parser_defaults():
    parsed = build_parser().parse_args([])
    assert parsed.dry_run is False
    assert parsed.probe == ""
    assert parsed.config == "config.yaml"
    assert parsed.sample == 0


def test_command_splitting():
    from popvpn.cli import _split_command

    assert _split_command(["--dry-run"]) == ("update", ["--dry-run"])
    assert _split_command(["parse", "a.txt"]) == ("parse", ["a.txt"])
    assert _split_command(["check-source", "https://x"]) == ("check-source", ["https://x"])
    assert _split_command([]) == ("update", [])


def test_version(capsys):
    assert main(["version"]) == 0
    assert "popvpn" in capsys.readouterr().out


def test_dry_run_json(workspace, capsys):
    code = main(
        [
            "--config", CONFIG,
            "--offline", str(DATA),
            "--dry-run",
            "--json",
            "--no-notify",
            "--quiet",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total"] == 13
    assert payload["by_protocol"]["vless"] == 3
    assert payload["files"] == []


def test_dry_run_prints_summary_line(workspace, capsys):
    code = main(["--config", CONFIG, "--offline", str(DATA), "--dry-run", "--no-notify", "--quiet"])
    assert code == 0
    out = capsys.readouterr().out
    assert "total=" in out and "dupes=" in out


def test_sample_prints_uris(workspace, capsys):
    main(
        [
            "--config", CONFIG,
            "--offline", str(DATA),
            "--dry-run",
            "--sample", "3",
            "--no-notify",
            "--quiet",
        ]
    )
    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith(("vless", "vmess", "trojan", "ss", "tuic", "hy2", "wireguard"))]
    assert len(lines) == 3
    assert all("#POPVPN" in line for line in lines)


def test_parse_command(capsys):
    code = main(["parse", str(DATA / "mixed.txt")])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total"] == 17
    assert payload["invalid"] == 2
    assert payload["by_protocol"]["vless"] == 7


def test_parse_without_arguments(capsys):
    assert main(["parse"]) == 2


def test_check_source_without_arguments(capsys):
    assert main(["check-source"]) == 2


def test_sources_command(workspace, capsys):
    code = main(["sources", "--config", CONFIG])
    assert code == 0
    out = capsys.readouterr().out
    assert "STATE" in out
    assert "patterniha" in out


def test_sources_command_missing_links_file(workspace, capsys, monkeypatch, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)
    assert main(["sources", "--config", CONFIG]) == 1
    assert "missing file" in capsys.readouterr().err


def test_bad_config_is_reported(workspace, capsys, tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("profile:\n  title: ok\n this line has no colon\n", encoding="utf-8")
    assert main(["--config", str(bad), "--dry-run", "--quiet"]) == 2
    assert "config error" in capsys.readouterr().err


def test_full_run_writes_files(workspace, capsys):
    code = main(
        [
            "--config", CONFIG,
            "--offline", str(DATA),
            "--no-notify",
            "--no-readme",
            "--quiet",
        ]
    )
    assert code == 0
    assert Path("working_configs.txt").exists()
    assert Path("outputs/clash.yaml").exists()
    # --no-readme must leave README untouched
    assert "CONFIGS-" not in Path("README.md").read_text(encoding="utf-8")
