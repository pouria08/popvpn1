from __future__ import annotations

from popvpn.protocols import (
    Config,
    decode_body,
    extract_uris,
    looks_like_error_page,
    normalize_line,
    parse_uri,
    rename,
)

VLESS = (
    "vless://a1b2c3d4-e5f6-4789-abcd-ef0123456789@185.238.228.10:443"
    "?security=reality&sni=www.microsoft.com&type=ws&path=%2Fx#🇩🇪 DE-Reality"
)


# ---------------------------------------------------------------------------
# normalize_line / extract_uris
# ---------------------------------------------------------------------------


def test_normalize_line_strips_and_unescapes():
    line = '  "vless://uuid@1.1.1.1:443?a=1&amp;b=2#name"  '
    assert normalize_line(line) == "vless://uuid@1.1.1.1:443?a=1&b=2#name"


def test_normalize_line_rejects_junk():
    assert normalize_line("# comment") is None
    assert normalize_line("") is None
    assert normalize_line("not a config") is None


def test_normalize_line_keeps_prefixed_lines():
    line = "3) vless://a1b2c3d4-e5f6-4789-abcd-ef0123456789@1.1.1.1:443?security=none#x"
    assert normalize_line(line) == line[3:]


def test_normalize_line_preserves_spaces_in_remark():
    line = "vless://a1b2c3d4-e5f6-4789-abcd-ef0123456789@1.1.1.1:443?security=none#🇩🇪 DE Frankfurt"
    assert normalize_line(line) == line


def test_extract_uris_splits_concatenated_stream():
    stream = VLESS + VLESS.replace("DE-Reality", "DE-Reality2")
    assert len(extract_uris(stream)) == 2


def test_extract_uris_ignores_noise():
    body = "hello world\n\n# comment\n" + VLESS + "\ngarbage\n"
    assert extract_uris(body) == [VLESS]


def test_decode_body_plain_passthrough():
    assert decode_body(VLESS) == VLESS


def test_decode_body_base64(data_dir):
    body = (data_dir / "base64_body.txt").read_text(encoding="utf-8")
    assert decode_body(body).startswith("vless://")


def test_decode_body_double_base64(data_dir):
    body = (data_dir / "double_base64_body.txt").read_text(encoding="utf-8")
    assert decode_body(body).startswith("vless://")


def test_error_page_detection(data_dir):
    assert looks_like_error_page((data_dir / "html_error.txt").read_text())
    assert looks_like_error_page((data_dir / "cloudflare_error.txt").read_text())
    assert not looks_like_error_page(VLESS)


# ---------------------------------------------------------------------------
# per protocol parsing
# ---------------------------------------------------------------------------


def test_vless_reality_fields():
    cfg = parse_uri(
        "vless://a1b2c3d4-e5f6-4789-abcd-ef0123456789@185.238.228.10:443"
        "?security=reality&sni=www.microsoft.com&pbk=AAA&sid=BBB"
        "&flow=xtls-rprx-vision&type=tcp#DE"
    )
    assert cfg is not None
    assert (cfg.protocol, cfg.host, cfg.port) == ("vless", "185.238.228.10", 443)
    assert cfg.security == "reality"
    assert cfg.sni == "www.microsoft.com"
    assert cfg.params["flow"] == "xtls-rprx-vision"
    assert cfg.remark == "DE"


def test_vless_requires_valid_uuid():
    assert parse_uri("vless://not-a-uuid@1.1.1.1:443?security=none#x") is None


def test_vless_requires_port():
    assert parse_uri("vless://a1b2c3d4-e5f6-4789-abcd-ef0123456789@1.1.1.1#x") is None


def test_vless_rejects_out_of_range_port():
    assert (
        parse_uri("vless://a1b2c3d4-e5f6-4789-abcd-ef0123456789@1.1.1.1:99999?security=none#x")
        is None
    )


def test_vmess_base64_json(data_dir, mixed_text):
    import base64
    import json

    payload = base64.b64encode(
        json.dumps(
            {
                "v": "2",
                "ps": "TR-Istanbul",
                "add": "95.179.143.12",
                "port": "8080",
                "id": "c3d4e5f6-a7b8-4901-bcde-012345678901",
                "aid": "0",
                "net": "ws",
                "host": "cdn2.example.com",
                "path": "/vmess",
                "tls": "tls",
            }
        ).encode()
    ).decode()
    cfg = parse_uri(f"vmess://{payload}")
    assert cfg is not None
    assert cfg.protocol == "vmess"
    assert cfg.host == "95.179.143.12"
    assert cfg.port == 8080
    assert cfg.network == "ws"
    assert cfg.security == "tls"
    assert cfg.remark == "TR-Istanbul"
    assert cfg.sni == "cdn2.example.com"


def test_vmess_querystring_form():
    import base64

    query = "remarks=US-East&add=vmess.example.com&port=443&id=e5f6a7b8-c9d0-4123-efab-234567890123&aid=0&net=tcp&tls=tls"
    payload = base64.b64encode(query.encode()).decode()
    cfg = parse_uri(f"vmess://{payload}")
    assert cfg is not None
    assert cfg.host == "vmess.example.com"
    assert cfg.remark == "US-East"
    assert cfg.security == "tls"


def test_vmess_legacy_is_flagged():
    import base64
    import json

    payload = base64.b64encode(
        json.dumps(
            {
                "v": "1",
                "ps": "legacy",
                "add": "legacy.example.com",
                "port": "443",
                "id": "d4e5f6a7-b8c9-4012-defa-123456789012",
                "aid": "64",
            }
        ).encode()
    ).decode()
    cfg = parse_uri(f"vmess://{payload}")
    assert cfg is not None
    assert cfg.legacy is True
    assert "legacy-vmess" in cfg.warnings


def test_vmess_rejects_garbage_payload():
    assert parse_uri("vmess://bm90LWJhc2U2NC1qc29u") is None


def test_trojan_parsing():
    cfg = parse_uri("trojan://secret@104.21.45.67:443?sni=trojan.example.com#FR")
    assert cfg is not None
    assert cfg.protocol == "trojan"
    assert cfg.secret == "secret"
    assert cfg.security == "tls"
    assert cfg.sni == "trojan.example.com"


def test_trojan_requires_password():
    assert parse_uri("trojan://@1.1.1.1:443#x") is None


def test_ss_sip002_form():
    import base64

    body = base64.b64encode(b"aes-256-gcm:sspassword").decode()
    cfg = parse_uri(f"ss://{body}@51.15.12.34:8389#GB")
    assert cfg is not None
    assert cfg.protocol == "ss"
    assert cfg.ss_method == "aes-256-gcm"
    assert cfg.secret == "sspassword"
    assert cfg.port == 8389


def test_ss_legacy_form():
    import base64

    body = base64.b64encode(b"chacha20-ietf-poly1305:pw@51.15.12.35:8389").decode()
    cfg = parse_uri(f"ss://{body}#legacy")
    assert cfg is not None
    assert cfg.host == "51.15.12.35"
    assert cfg.ss_method == "chacha20-ietf-poly1305"


def test_ss_shadowsocks_scheme_alias():
    import base64

    body = base64.b64encode(b"aes-128-gcm:pw").decode()
    cfg = parse_uri(f"shadowsocks://{body}@1.2.3.4:8388#alias")
    assert cfg is not None and cfg.protocol == "ss"


def test_ss_plugin_is_flagged():
    import base64

    body = base64.b64encode(b"aes-256-gcm:pw").decode()
    cfg = parse_uri(f"ss://{body}@1.2.3.4:8388?plugin=obfs-local#plugin")
    assert "plugin" in cfg.warnings


def test_tuic_parsing():
    cfg = parse_uri(
        "tuic://d4e5f6a7-b8c9-4012-defa-123456789012:pass@tuic.example.com:443?sni=tuic.example.com#SE"
    )
    assert cfg is not None
    assert cfg.protocol == "tuic"
    assert cfg.params["password"] == "pass"


def test_hy2_parsing():
    cfg = parse_uri("hy2://pw@77.238.120.11:443?sni=hy2.example.com#FI")
    assert cfg is not None and cfg.protocol == "hy2"
    assert cfg.host == "77.238.120.11"


def test_wireguard_parsing():
    cfg = parse_uri(
        "wireguard://PUBKEY@162.159.192.1:2408?privateKey=PRIVKEY&address=172.16.0.2%2F32#US"
    )
    assert cfg is not None and cfg.protocol == "wireguard"
    assert cfg.params["privatekey"] == "PRIVKEY"


def test_unknown_scheme_is_rejected():
    assert parse_uri("http://example.com") is None
    assert parse_uri("socks://1.1.1.1:1080") is None


def test_ipv6_host():
    cfg = parse_uri("trojan://pw@[2001:db8::1]:443?sni=x.example#v6")
    assert cfg is not None
    assert cfg.host == "2001:db8::1"
    assert cfg.port == 443


# ---------------------------------------------------------------------------
# dedupe fingerprints and renaming
# ---------------------------------------------------------------------------


def test_fingerprint_ignores_remark():
    a = parse_uri(VLESS)
    b = parse_uri(VLESS.split("#")[0] + "#something else")
    assert a.fingerprint == b.fingerprint


def test_fingerprint_differs_on_port():
    a = parse_uri(VLESS)
    b = parse_uri(VLESS.replace(":443?", ":8443?"))
    assert a.fingerprint != b.fingerprint


def test_rename_plain_uri():
    renamed = rename(VLESS, "POPVPN | 0001 | DE")
    assert renamed.endswith("#POPVPN | 0001 | DE")
    assert renamed.startswith(VLESS.split("#")[0])


def test_rename_vmess_rewrites_ps_field():
    import base64
    import json

    payload = base64.b64encode(json.dumps({"v": "2", "ps": "old", "add": "1.1.1.1", "port": "443", "id": "e5f6a7b8-c9d0-4123-efab-234567890123"}).encode()).decode()
    renamed = rename(f"vmess://{payload}", "POPVPN | 0002 | TR")
    decoded = json.loads(base64.b64decode(renamed.split("://", 1)[1]))
    assert decoded["ps"] == "POPVPN | 0002 | TR"
    assert "#" not in renamed


def test_rename_vmess_query_form():
    import base64

    query = "remarks=old&add=1.1.1.1&port=443&id=e5f6a7b8-c9d0-4123-efab-234567890123"
    payload = base64.b64encode(query.encode()).decode()
    renamed = rename(f"vmess://{payload}", "NEW NAME")
    decoded = base64.b64decode(renamed.split("://", 1)[1]).decode()
    assert "remarks=NEW+NAME" in decoded
    assert "old" not in decoded


def test_rename_ss_legacy_roundtrip():
    import base64

    body = base64.b64encode(b"aes-256-gcm:pw@1.2.3.4:8388").decode()
    renamed = rename(f"ss://{body}#old", "GB | 0007")
    assert renamed.endswith("#GB | 0007")
    assert parse_uri(renamed) is not None


def test_remark_is_sanitised():
    renamed = rename(VLESS, "bad\nname#with hash")
    assert "\n" not in renamed
    assert renamed.count("#") == 1


def test_parse_many_counts(mixed_text):
    from popvpn.protocols import parse_many

    configs = parse_many(mixed_text, source="fixture")
    assert len(configs) >= 15
    assert all(cfg.source == "fixture" for cfg in configs)
    assert {cfg.protocol for cfg in configs} >= {"vless", "vmess", "trojan", "ss"}


def test_config_endpoint_and_dict():
    cfg: Config = parse_uri(VLESS)
    assert cfg.endpoint == "185.238.228.10:443"
    payload = cfg.as_dict()
    assert payload["protocol"] == "vless"
    assert "secret" not in payload
