from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import commit_message  # noqa: E402
import pr_comment  # noqa: E402
import verify_outputs  # noqa: E402

from popvpn.pipeline import Options, run  # noqa: E402

CONFIG = str(ROOT / "tests" / "pipeline-config.yaml")
DATA = str(ROOT / "tests" / "data")


@pytest.fixture()
def generated(workspace):
    """A complete, real pipeline run inside the temporary workspace."""

    result = run(
        Options(
            config_path=CONFIG,
            offline_dir=DATA,
            notify_enabled=False,
            quiet=True,
        )
    )
    return result


def test_verify_outputs_passes_on_a_real_run(generated, capsys):
    assert verify_outputs.verify(Path.cwd()) == []
    assert "[verify] OK" in capsys.readouterr().out


def test_verify_outputs_detects_corrupted_base64(generated, capsys):
    import base64

    Path("base64.txt").write_text(base64.b64encode(b"vless://tampered\n").decode(), encoding="utf-8")
    errors = verify_outputs.verify(Path.cwd())
    assert any("does not match" in error for error in errors)
    assert "[verify] FAILED" in capsys.readouterr().out


def test_verify_outputs_detects_unparseable_uri(generated, capsys):
    text = Path("working_configs.txt").read_text(encoding="utf-8")
    Path("working_configs.txt").write_text(text + "\nvless://broken@1.1.1.1:443#bad\n", encoding="utf-8")
    errors = verify_outputs.verify(Path.cwd())
    assert any("do not re-parse" in error for error in errors)


def test_verify_outputs_reports_missing_files(tmp_path, capsys):
    errors = verify_outputs.verify(tmp_path)
    assert len(errors) == 3
    assert all("missing" in error for error in errors)


def test_verify_outputs_detects_bad_clash_yaml(generated):
    Path("outputs/clash.yaml").write_text("proxies:\n  - this is: [broken\n", encoding="utf-8")
    errors = verify_outputs.verify(Path.cwd())
    assert any("clash.yaml" in error for error in errors)


def test_verify_outputs_detects_bad_singbox_json(generated):
    Path("outputs/singbox.json").write_text("{not json", encoding="utf-8")
    errors = verify_outputs.verify(Path.cwd())
    assert any("singbox.json" in error for error in errors)


def test_commit_message_from_generated_stats(generated, capsys):
    stats = json.loads(Path("outputs/stats.json").read_text(encoding="utf-8"))
    subject = commit_message.build_message(stats)
    assert subject.startswith("Auto-Update: Total: 24")
    assert "TROJAN: 12" in subject
    # Two synthetic HTML/CDN error fixtures are correctly rejected as feeds.
    assert "Sources: 4/6" in subject
    assert len(subject) <= 180

    body = commit_message.build_body(stats)
    assert "duplicates removed: 16" in body
    assert "countries detected: 12" in body


def test_commit_message_truncates_long_subject():
    stats = {"total": 1, "by_protocol": {f"proto{i}": i for i in range(30)}, "sources": {"ok": 1, "total": 1}}
    assert len(commit_message.build_message(stats)) <= 180


def test_commit_message_cli(generated, capsys):
    assert commit_message.main(["outputs/stats.json"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("Auto-Update:")


def test_commit_message_cli_missing_file(tmp_path, capsys):
    assert commit_message.main([str(tmp_path / "nope.json")]) == 1
    assert "stats file not found" in capsys.readouterr().err


def test_pr_comment_from_generated_stats(generated):
    stats = json.loads(Path("outputs/stats.json").read_text(encoding="utf-8"))
    comment = pr_comment.build_comment(stats)
    assert "POPVPN X — live pipeline run" in comment
    assert "**24 configs**" in comment
    assert "| TROJAN | 12 |" in comment
    assert "verify_outputs.py" in comment


def test_pr_comment_handles_empty_stats():
    comment = pr_comment.build_comment({})
    assert "**0 configs**" in comment


def test_pr_comment_cli(generated, capsys):
    assert pr_comment.main(["outputs/stats.json"]) == 0
    assert "live pipeline run" in capsys.readouterr().out


def test_pr_comment_cli_missing_file(tmp_path, capsys):
    assert pr_comment.main([str(tmp_path / "nope.json")]) == 1
