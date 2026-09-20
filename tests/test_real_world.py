"""Regression tests against a real-world subscription body.

``tests/data/real_trojan_sample.txt`` is a trimmed excerpt of a public feed
and covers the shapes that synthetic fixtures miss: profile header lines,
Persian remarks, emoji flags, JSON inside a query parameter, ``xhttp``
transport, and — most importantly — a Trojan password that contains a ``#``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from popvpn.protocols import decode_body, extract_uris, parse_uri, rename

SAMPLE = Path(__file__).parent / "data" / "real_trojan_sample.txt"


@pytest.fixture(scope="module")
def parsed():
    text = SAMPLE.read_text(encoding="utf-8")
    chunks = extract_uris(decode_body(text))
    return chunks, [cfg for cfg in (parse_uri(chunk) for chunk in chunks) if cfg]


def test_every_real_line_parses(parsed):
    chunks, configs = parsed
    assert len(chunks) == 13
    assert len(configs) == 13, "every config in the real sample must parse"


def test_profile_header_lines_are_ignored(parsed):
    text = SAMPLE.read_text(encoding="utf-8")
    headers = [line for line in text.splitlines() if line.startswith("#profile-")]
    assert len(headers) >= 2
    # none of them became a config
    assert all(cfg.protocol == "trojan" for cfg in parsed[1])


def test_hash_inside_password_survives(parsed):
    _, configs = parsed
    cfg = next(c for c in configs if c.host == "104.16.7.70")
    assert cfg.secret == "8r<[9'l6hAO#8ZQi"
    assert cfg.port == 443
    assert cfg.sni == "koma-yt.pages.dev"


def test_rename_keeps_a_hash_password_intact(parsed):
    _, configs = parsed
    cfg = next(c for c in configs if c.host == "104.16.7.70")
    renamed = rename(cfg.raw, "POPVPN | 0007 | CA")
    assert renamed.endswith("#POPVPN | 0007 | CA")
    again = parse_uri(renamed)
    assert again is not None
    assert again.secret == cfg.secret
    assert again.host == cfg.host


def test_remark_variants_dedupe(parsed):
    _, configs = parsed
    fingerprints = [cfg.fingerprint for cfg in configs]
    assert len(set(fingerprints)) == 11, "two configs are re-published with another remark"


def test_real_reality_config_is_recognised(parsed):
    _, configs = parsed
    reality = [cfg for cfg in configs if cfg.security == "reality"]
    assert reality, "the sample contains a Reality endpoint"
    assert reality[0].params["pbk"]
    assert reality[0].sni == "www.yahoo.com"


def test_real_insecure_config_is_flagged(parsed):
    _, configs = parsed
    from popvpn.security import audit

    _, report = audit(configs, {})
    assert report.insecure >= 2
    assert report.warnings.get("allow-insecure", 0) >= 2


def test_xhttp_transport_with_json_extra(parsed):
    _, configs = parsed
    xhttp = next(cfg for cfg in configs if cfg.network == "xhttp")
    assert xhttp.host.endswith("iranpuls.ir")
    assert "xPaddingBytes" in xhttp.params.get("extra", "")


def test_persian_remark_is_preserved(parsed):
    _, configs = parsed
    assert any("حرام" in cfg.remark for cfg in configs)


def test_geo_detection_on_real_remarks(parsed):
    from popvpn import geo

    codes = {geo.detect(cfg.remark).code for cfg in parsed[1]}
    assert "ID" in codes or "CA" in codes, f"expected a detected country, got {codes}"


def test_clash_export_of_real_configs(parsed):
    yaml = pytest.importorskip("yaml")

    from popvpn import geo, naming, writers

    configs = parsed[1]
    for cfg in configs:
        detected = geo.detect(cfg.remark)
        cfg.geo_code, cfg.geo_name, cfg.geo_flag = detected.code, detected.name, detected.flag
    naming.apply_names(configs, template="{brand} {index}", brand="POPVPN")
    document = yaml.safe_load(writers.clash_document(configs, {"title": "POPVPN X"}))
    assert len(document["proxies"]) == len(configs)
    assert all(proxy["type"] == "trojan" for proxy in document["proxies"])
    # a password containing '#' must survive the YAML round trip
    assert any("#" in str(proxy.get("password", "")) for proxy in document["proxies"])
