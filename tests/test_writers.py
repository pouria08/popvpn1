from __future__ import annotations

import base64
import json

import pytest

from popvpn import geo, naming, writers
from popvpn.protocols import parse_uri

yaml = pytest.importorskip("yaml")

PROFILE = {"title": "POPVPN X", "update_interval": 1, "total": 10, "expire": 99}

SAMPLES = [
    (
        "vless://a1b2c3d4-e5f6-4789-abcd-ef0123456789@185.238.228.10:443"
        "?security=reality&sni=www.microsoft.com&fp=chrome&pbk=PUBKEY&sid=SID"
        "&flow=xtls-rprx-vision&type=tcp#🇩🇪 DE-Reality"
    ),
    (
        "vless://b2c3d4e5-f6a7-4890-bcde-f01234567890@45.131.4.207:2087"
        "?type=ws&security=tls&sni=cdn.example.com&path=%2Fws#🇳🇱 NL-WS"
    ),
    "trojan://pw@104.21.45.67:443?sni=trojan.example.com#🇫🇷 FR",
    "ss://" + base64.b64encode(b"aes-256-gcm:sspw").decode() + "@51.15.12.34:8389#🇬🇧 GB",
    "hy2://hy2pw@77.238.120.11:443?sni=hy2.example.com#🇫🇮 FI",
    (
        "tuic://d4e5f6a7-b8c9-4012-defa-123456789012:tuicpw@tuic.example.com:443"
        "?sni=tuic.example.com&congestion_control=bbr#🇸🇪 SE"
    ),
    "wireguard://PUBKEY@162.159.192.1:2408?privateKey=PRIV&address=172.16.0.2%2F32#🇺🇸 US",
]


@pytest.fixture()
def configs():
    parsed = [parse_uri(uri) for uri in SAMPLES]
    assert all(parsed), "fixtures must parse"
    for cfg in parsed:
        detected = geo.detect(cfg.remark)
        cfg.geo_code, cfg.geo_name, cfg.geo_flag = detected.code, detected.name, detected.flag
    uris = naming.apply_names(parsed, template="{brand} {index} {country}", brand="POPVPN")
    return parsed, uris


def test_plain_subscription_has_hiddify_header(configs):
    _, uris = configs
    text = writers.plain_subscription(uris, PROFILE)
    assert text.startswith("#profile-title: POPVPN X")
    assert "#profile-update-interval: 1" in text
    assert "#subscription-userinfo: upload=0; download=0; total=10; expire=99" in text
    assert all(uri in text for uri in uris)


def test_profile_header_optional_fields():
    header = writers.profile_header(
        {"title": "T", "support_url": "https://t.me/x", "announce": "hello"}
    )
    assert "#support-url: https://t.me/x" in header
    assert "#announce: hello" in header


def test_base64_round_trip(configs):
    _, uris = configs
    encoded = writers.base64_subscription(uris)
    decoded = base64.b64decode(encoded).decode()
    assert decoded.splitlines() == list(uris)


def test_group_by_protocol_and_country(configs):
    parsed, uris = configs
    by_protocol = writers.group_by_protocol(parsed, uris)
    assert set(by_protocol) == {"vless", "trojan", "ss", "hy2", "tuic", "wireguard"}
    assert len(by_protocol["vless"]) == 2
    by_country = writers.group_by_country(parsed, uris)
    assert "DE" in by_country and "NL" in by_country


def test_clash_yaml_is_valid(configs):
    parsed, _ = configs
    document = yaml.safe_load(writers.clash_document(parsed, PROFILE))
    assert isinstance(document, dict)
    assert document["mixed-port"] == 7890
    proxies = document["proxies"]
    assert len(proxies) == len(parsed)
    types = {proxy["type"] for proxy in proxies}
    assert {"vless", "trojan", "ss", "hysteria2", "tuic", "wireguard"} <= types

    vless = next(p for p in proxies if p["type"] == "vless" and p.get("reality-opts"))
    assert vless["reality-opts"]["public-key"] == "PUBKEY"
    assert vless["reality-opts"]["short-id"] == "SID"
    assert vless["client-fingerprint"] == "chrome"
    assert vless["flow"] == "xtls-rprx-vision"

    ws = next(p for p in proxies if p.get("network") == "ws")
    assert ws["ws-opts"]["path"] == "/ws"
    assert ws["ws-opts"]["headers"]["Host"] == "cdn.example.com"

    trojan = next(p for p in proxies if p["type"] == "trojan")
    assert trojan["sni"] == "trojan.example.com"

    groups = {group["name"]: group for group in document["proxy-groups"]}
    assert "AUTO" in groups and "SELECT" in groups
    assert groups["VLESS"]["type"] == "url-test"
    assert document["rules"][-1] == "MATCH,SELECT"


def test_clash_names_with_special_characters_are_quoted(configs):
    parsed, _ = configs
    for cfg in parsed:
        cfg.name = 'name with "quotes": and #hash'
    document = yaml.safe_load(writers.clash_document(parsed, PROFILE))
    assert document["proxies"][0]["name"] == 'name with "quotes": and #hash'


def test_singbox_json_is_valid(configs):
    parsed, _ = configs
    document = json.loads(writers.singbox_document(parsed, PROFILE))
    outbounds = document["outbounds"]
    tags = {ob["tag"] for ob in outbounds}
    assert {"select", "direct", "block", "dns"} <= tags
    vless = next(ob for ob in outbounds if ob["type"] == "vless")
    assert vless["tls"]["reality"]["public_key"] == "PUBKEY"
    assert vless["flow"] == "xtls-rprx-vision"
    ss = next(ob for ob in outbounds if ob["type"] == "shadowsocks")
    assert ss["method"] == "aes-256-gcm"
    assert document["route"]["final"] == "select"


def test_clash_proxy_skips_unknown_protocol():
    cfg = parse_uri(SAMPLES[0])
    cfg.protocol = "unknown"
    assert writers.clash_proxy(cfg) is None


def test_yaml_scalar_quoting():
    assert writers._yaml_scalar(True) == "true"
    assert writers._yaml_scalar(None) == "null"
    assert writers._yaml_scalar(42) == "42"
    assert writers._yaml_scalar("plain") == "plain"
    assert writers._yaml_scalar("true") == '"true"'
    assert writers._yaml_scalar("has: colon") == '"has: colon"'
    assert writers._yaml_scalar("123") == '"123"'
    assert writers._yaml_scalar("") == '""'


def test_written_tracks_sizes(tmp_path):
    sink = writers.Written()
    sink.add(tmp_path / "a.txt", "hello")
    sink.add(tmp_path / "nested" / "b.txt", b"world")
    assert sink.total_bytes == 10
    assert (tmp_path / "nested" / "b.txt").read_bytes() == b"world"
