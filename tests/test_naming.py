from __future__ import annotations

from popvpn import geo, naming
from popvpn.protocols import parse_uri

VLESS = (
    "vless://a1b2c3d4-e5f6-4789-abcd-ef0123456789@185.238.228.10:443"
    "?security=reality&sni=www.microsoft.com&type=tcp#🇩🇪 DE-Frankfurt"
)


def _cfg(uri: str = VLESS):
    cfg = parse_uri(uri)
    detected = geo.detect(cfg.remark)
    cfg.geo_code, cfg.geo_name, cfg.geo_flag = detected.code, detected.name, detected.flag
    return cfg


def test_template_render():
    cfg = _cfg()
    name = naming.render_name(
        cfg,
        42,
        template="{brand} {index} {flag} {country} {protocol} {transport}",
        brand="POPVPN",
        index_width=4,
    )
    assert name == "POPVPN 0042 🇩🇪 DE VLESS REALITY"


def test_empty_placeholders_collapse():
    cfg = _cfg("trojan://pw@1.2.3.4:443?sni=x.example#no-geo-here")
    name = naming.render_name(
        cfg,
        1,
        template="{brand} {index} {flag} {country} {protocol} {transport}",
        brand="POPVPN",
        index_width=3,
        unknown_label="GLOBAL",
    )
    assert "  " not in name
    assert name.startswith("POPVPN 001 GLOBAL TROJAN")


def test_max_length_is_respected():
    cfg = _cfg()
    name = naming.render_name(
        cfg,
        1,
        template="{brand} {index} {flag} {country} {protocol} {transport} {host} {port} {sni}",
        brand="POPVPN",
        max_length=30,
    )
    assert len(name) <= 30


def test_transport_labels():
    cases = {
        "vless://a1b2c3d4-e5f6-4789-abcd-ef0123456789@1.1.1.1:443?security=reality#x": "REALITY",
        "vless://a1b2c3d4-e5f6-4789-abcd-ef0123456789@1.1.1.1:443?type=ws&security=tls#x": "WS",
        "vless://a1b2c3d4-e5f6-4789-abcd-ef0123456789@1.1.1.1:443?type=grpc&security=tls#x": "GRPC",
        "trojan://pw@1.1.1.1:443#x": "TLS",
    }
    for uri, expected in cases.items():
        assert naming.transport_label(parse_uri(uri)) == expected, uri


def test_apply_names_rewrites_uris_and_dedupes_names():
    configs = [_cfg(), _cfg()]
    uris = naming.apply_names(
        configs,
        template="{brand} {index} {country}",
        brand="POPVPN",
        index_width=3,
        unique=True,
    )
    assert len(uris) == 2
    assert uris[0].endswith("#POPVPN 001 DE")
    assert uris[1].endswith("#POPVPN 002 DE")
    assert configs[0].name != configs[1].name
    # the URI itself must stay parseable
    assert parse_uri(uris[0]) is not None
    assert parse_uri(uris[1]) is not None


def test_apply_names_unique_suffix_on_collision():
    configs = [_cfg(), _cfg()]
    uris = naming.apply_names(
        configs,
        template="{brand}",
        brand="POPVPN",
        unique=True,
    )
    assert uris[0].endswith("#POPVPN")
    assert uris[1].endswith("#POPVPN 2")


def test_unknown_placeholder_is_ignored():
    cfg = _cfg()
    name = naming.render_name(
        cfg, 1, template="{brand} {nope}", brand="POPVPN", max_length=40
    )
    assert name == "POPVPN"
