from __future__ import annotations

from popvpn.protocols import parse_uri
from popvpn.scoring import score, sort_configs
from popvpn.security import audit, is_private_host

GOOD = (
    "vless://a1b2c3d4-e5f6-4789-abcd-ef0123456789@185.238.228.10:443"
    "?security=reality&sni=www.microsoft.com&fp=chrome&pbk=AAA&sid=BBB"
    "&flow=xtls-rprx-vision&type=tcp#🇩🇪 DE"
)
PLAIN = "vless://b2c3d4e5-f6a7-4890-bcde-f01234567890@1.2.3.4:80?security=none&type=tcp#XX"
INSECURE = (
    "vless://c3d4e5f6-a7b8-4901-bcde-012345678901@192.168.1.5:443"
    "?security=tls&allowInsecure=1#private"
)


def test_reality_beats_plain_tcp():
    good = score(parse_uri(GOOD))
    plain = score(parse_uri(PLAIN))
    assert good > plain


def test_score_is_bounded():
    for uri in (GOOD, PLAIN, INSECURE):
        value = score(parse_uri(uri))
        assert 0.0 <= value <= 100.0


def test_verified_boosts_score():
    cfg = parse_uri(GOOD)
    base = score(cfg)
    cfg.verified = True
    cfg.latency_ms = 120
    boosted = score(cfg)
    cfg.verified = False
    penalised = score(cfg)
    assert boosted > base > penalised


def test_source_reliability_matters():
    cfg = parse_uri(GOOD)
    high = score(cfg, source_reliability=1.0)
    low = score(cfg, source_reliability=0.0)
    assert high > low


def test_sort_by_score_is_deterministic():
    from popvpn.scoring import score_all

    configs = [parse_uri(uri) for uri in (PLAIN, GOOD, INSECURE)]
    score_all(configs)
    first = sort_configs(configs, "score")
    second = sort_configs(configs, "score")
    assert [c.host for c in first] == [c.host for c in second]
    assert first[0].host == "185.238.228.10"
    assert first[0].score >= first[-1].score


def test_sort_modes():
    configs = [parse_uri(uri) for uri in (PLAIN, GOOD)]
    assert {c.host for c in sort_configs(configs, "protocol")} == {c.host for c in configs}
    assert sort_configs(configs, "country") is not None
    assert sort_configs(configs, "latency") is not None


def test_is_private_host():
    assert is_private_host("127.0.0.1")
    assert is_private_host("192.168.1.5")
    assert is_private_host("10.0.0.1")
    assert is_private_host("::1")
    assert not is_private_host("185.238.228.10")
    assert not is_private_host("example.com")
    assert not is_private_host("")


def test_audit_flags_but_keeps_by_default():
    configs = [parse_uri(uri) for uri in (GOOD, PLAIN, INSECURE)]
    kept, report = audit(configs, {})
    assert len(kept) == 3
    assert report.dropped == 0
    assert report.private_hosts == 1
    assert report.insecure == 1
    assert "allow-insecure" in report.warnings


def test_audit_drop_options():
    configs = [parse_uri(uri) for uri in (GOOD, INSECURE)]
    kept, report = audit(configs, {"drop_insecure": True, "drop_private_hosts": True})
    assert len(kept) == 1
    assert kept[0].host == "185.238.228.10"
    assert report.dropped == 1
    assert report.dropped_reasons


def test_audit_flags_placeholder_credentials():
    cfg = parse_uri("trojan://00000000-0000-0000-0000-000000000000@1.2.3.4:443#x")
    kept, report = audit([cfg], {})
    assert "weak-credential" in kept[0].warnings
    assert report.placeholder_credentials == 1


def test_audit_max_warnings():
    cfg = parse_uri(INSECURE)
    cfg.warnings += ["a", "b", "c"]
    kept, report = audit([cfg], {"max_warnings": 2})
    assert kept == []
    assert report.dropped_reasons.get("too-many-warnings") == 1


def test_report_serialises():
    _, report = audit([parse_uri(GOOD)], {})
    payload = report.as_dict()
    assert payload["kept"] == 1
    assert isinstance(payload["warnings"], dict)
