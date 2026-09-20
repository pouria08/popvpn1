"""Regenerate the test fixtures in ``tests/data``.

    python tests/make_fixtures.py

The fixtures are synthetic — no real credentials — but they cover the shapes
that real free feeds produce (HTML-escaped entities, Base64 bodies, VMess in
both encodings, legacy Shadowsocks, concatenated lines, error pages).
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

DATA = Path(__file__).parent / "data"

VLESS_REALITY = (
    "vless://a1b2c3d4-e5f6-4789-abcd-ef0123456789@185.238.228.10:443"
    "?encryption=none&flow=xtls-rprx-vision&security=reality&sni=www.microsoft.com"
    "&fp=chrome&pbk=SbVKOEMjK0sIlbwg4akyBg5mL5BZ6BTOs5FA65m4VTE&sid=6c8857e3"
    "&type=tcp&headerType=none#"
    "🇩🇪 DE-Frankfurt-Reality"
)
VLESS_WS = (
    "vless://b2c3d4e5-f6a7-4890-bcde-f01234567890@45.131.4.207:2087"
    "?type=ws&security=tls&sni=cdn.example.com&host=cdn.example.com"
    "&path=%2Fvless-ws&alpn=h2%2Chttp%2F1.1#"
    "🇳🇱 NL-Amsterdam-WS"
)
VLESS_INSECURE = (
    "vless://c3d4e5f6-0000-4000-8000-012345678901@192.168.1.10:8443"
    "?security=tls&sni=insecure.example.com&allowInsecure=1&type=tcp#INSECURE-PRIVATE"
)
VMESS_JSON = {
    "v": "2",
    "ps": "🇹🇷 TR-Istanbul-VMess",
    "add": "95.179.143.12",
    "port": "8080",
    "id": "c3d4e5f6-a7b8-4901-bcde-012345678901",
    "aid": "0",
    "scy": "auto",
    "net": "ws",
    "type": "",
    "host": "cdn2.example.com",
    "path": "/vmess",
    "tls": "",
}
VMESS_LEGACY = {
    "v": "1",
    "ps": "LEGACY-VMess-IT2",
    "add": "legacy.example.com",
    "port": "443",
    "id": "d4e5f6a7-b8c9-4012-defa-123456789012",
    "aid": "64",
    "net": "tcp",
    "tls": "tls",
}
VMESS_QUERY = (
    "remarks=US-NewYork-VMess-Query&add=vmess.example.com&port=443"
    "&id=e5f6a7b8-c9d0-4123-efab-234567890123&aid=0&net=ws&host=cdn3.example.com"
    "&path=%2Fws&tls=tls&sni=cdn3.example.com"
)
TROJAN = (
    "trojan://trojanpassword123@104.21.45.67:443"
    "?security=tls&sni=trojan.example.com&type=tcp&allowInsecure=0#🇫🇷 FR-Paris-Trojan"
)
SS_BODY = "aes-256-gcm:sspassword123"
SS_SIP002 = (
    "ss://"
    + base64.b64encode(SS_BODY.encode()).decode()
    + "@51.15.12.34:8389#🇬🇧 GB-London-SS"
)
SS_LEGACY = (
    "ss://"
    + base64.b64encode(f"{SS_BODY}@51.15.12.35:8389".encode()).decode()
    + "#GB-London-SS-Legacy"
)
SS_PLUGIN = (
    "ss://"
    + base64.b64encode("chacha20-ietf-poly1305:pluginpass".encode()).decode()
    + "@51.15.12.36:8390?plugin=obfs-local%3Bobfs%3Dhttp#DE-Frankfurt-SS-Obfs"
)
TUIC = (
    "tuic://d4e5f6a7-b8c9-4012-defa-123456789012:tui%40password@tuic.example.com:443"
    "?congestion_control=bbr&alpn=h3&sni=tuic.example.com#🇸🇪 SE-Stockholm-TUIC"
)
HY2 = (
    "hy2://hy2password@77.238.120.11:443?sni=hy2.example.com&insecure=1#🇫🇮 FI-Helsinki-HY2"
)
WIREGUARD = (
    "wireguard://PUBLICKEY0000000000000000000000000000000000000000="
    "@162.159.192.1:2408"
    "?privateKey=PRIVATEKEY00000000000000000000000000000000000=&address=172.16.0.2%2F32"
    "#🇺🇸 US-Cloudflare-WG"
)

HTML_ESCAPED = VLESS_WS.replace("&", "&amp;")  # entity-encoded copy


def _vmess_json_uri() -> str:
    payload = base64.b64encode(json.dumps(VMESS_JSON, ensure_ascii=False).encode()).decode()
    return f"vmess://{payload}"


def _vmess_legacy_uri() -> str:
    payload = base64.b64encode(json.dumps(VMESS_LEGACY).encode()).decode()
    return f"vmess://{payload}"


def _vmess_query_uri() -> str:
    payload = base64.b64encode(VMESS_QUERY.encode()).decode()
    return f"vmess://{payload}"


def write_mixed() -> None:
    lines = [
        "# POPVPN X test fixture — mixed protocols",
        "",
        VLESS_REALITY,
        VLESS_WS,
        VLESS_INSECURE,
        _vmess_json_uri(),
        _vmess_legacy_uri(),
        _vmess_query_uri(),
        TROJAN,
        SS_SIP002,
        SS_LEGACY,
        SS_PLUGIN,
        TUIC,
        HY2,
        WIREGUARD,
        "   " + VLESS_REALITY + "   ",  # whitespace padded duplicate
        HTML_ESCAPED,  # HTML-entity duplicate
        VLESS_REALITY + VLESS_WS,  # two URIs concatenated on one line
        "this line is not a config",
        "vless://not-a-uuid@example.com:443#broken",
        "vmess://bm90LWJhc2U2NC1qc29u#broken-vmess",
        "",
    ]
    (DATA / "mixed.txt").write_text("\n".join(lines), encoding="utf-8")


def write_base64() -> None:
    body = "\n".join(
        [
            VLESS_REALITY,
            VLESS_WS,
            TROJAN,
            SS_SIP002,
            _vmess_json_uri(),
        ]
    )
    (DATA / "base64_body.txt").write_text(
        base64.b64encode(body.encode()).decode(), encoding="utf-8"
    )
    (DATA / "double_base64_body.txt").write_text(
        base64.b64encode(base64.b64encode(body.encode()).decode().encode()).decode(),
        encoding="utf-8",
    )


def write_error_pages() -> None:
    (DATA / "html_error.txt").write_text(
        "<!DOCTYPE html>\n<html><head><title>404 Not Found</title></head>"
        "<body>Nothing here</body></html>\n",
        encoding="utf-8",
    )
    (DATA / "cloudflare_error.txt").write_text(
        "<html><head><title>Error 1027</title></head>"
        "<body>The worker exceeded the number of free subrequest</body></html>\n",
        encoding="utf-8",
    )


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    write_mixed()
    write_base64()
    write_error_pages()
    print(f"fixtures written to {DATA}")


if __name__ == "__main__":
    main()
