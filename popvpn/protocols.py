"""Parsing, validation and normalisation of VPN subscription URIs.

Supported protocols
-------------------
VLESS, VMess (Base64-JSON *and* Base64-querystring forms), Trojan,
Shadowsocks (SIP002 *and* legacy fully-encoded form), TUIC, Hysteria,
Hysteria2 and WireGuard.

Every public function here is side-effect free so the whole module can be
unit-tested without touching the network.
"""

from __future__ import annotations

import base64
import binascii
import html
import json
import re
import uuid as _uuid
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, unquote

# ---------------------------------------------------------------------------
# Protocol registry
# ---------------------------------------------------------------------------

SCHEME_ALIASES = {
    "vless": "vless",
    "vmess": "vmess",
    "trojan": "trojan",
    "ss": "ss",
    "shadowsocks": "ss",
    "tuic": "tuic",
    "hy2": "hy2",
    "hysteria2": "hy2",
    "hysteria": "hysteria",
    "wireguard": "wireguard",
    "wg": "wireguard",
}

PROTOCOL_LABEL = {
    "vless": "VLESS",
    "vmess": "VMess",
    "trojan": "Trojan",
    "ss": "Shadowsocks",
    "tuic": "TUIC",
    "hy2": "Hysteria2",
    "hysteria": "Hysteria",
    "wireguard": "WireGuard",
}

#: Protocols the original POPVPN published, kept first so the default
#: ``protocols`` filter behaves like a drop-in replacement.
LEGACY_PROTOCOLS = ("vless", "vmess", "trojan", "ss")

ALL_PROTOCOLS = tuple(PROTOCOL_LABEL)

KNOWN_SS_METHODS = {
    "aes-128-gcm",
    "aes-192-gcm",
    "aes-256-gcm",
    "aes-128-cfb",
    "aes-192-cfb",
    "aes-256-cfb",
    "aes-128-ctr",
    "aes-192-ctr",
    "aes-256-ctr",
    "chacha20",
    "chacha20-ietf",
    "chacha20-ietf-poly1305",
    "chacha20-poly1305",
    "xchacha20-ietf-poly1305",
    "rc4-md5",
    "plain",
    "none",
    "2022-blake3-aes-128-gcm",
    "2022-blake3-aes-256-gcm",
    "2022-blake3-chacha20-poly1305",
}

KNOWN_NETWORKS = {
    "tcp",
    "ws",
    "websocket",
    "grpc",
    "gun",
    "multi",
    "kcp",
    "mkcp",
    "quic",
    "h2",
    "http",
    "httpupgrade",
    "splithttp",
    "xhttp",
    "raw",
    "packetencoding",
    "",
}

KNOWN_SECURITY = {"none", "tls", "reality", "xtls", "reality-tls", ""}

_URI_RE = re.compile(
    r"(?:vless|vmess|trojan|shadowsocks|ss|tuic|hy2|hysteria2|hysteria|wireguard|wg)://",
    re.IGNORECASE,
)

_HTMLISH_RE = re.compile(r"&(?:amp|quot|lt|gt|#\d+|#x[0-9a-fA-F]+);")
_B64_BODY_RE = re.compile(r"^[A-Za-z0-9+/\-_]+={0,2}$")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Config:
    """A single parsed and validated subscription entry."""

    raw: str
    scheme: str
    protocol: str
    host: str = ""
    port: int = 0
    secret: str = ""
    network: str = "tcp"
    security: str = "none"
    sni: str = ""
    remark: str = ""
    source: str = ""
    fingerprint: str = ""
    params: dict = field(default_factory=dict)
    vmess_json: dict | None = None
    ss_method: str = ""
    ss_body: str = ""
    legacy: bool = False
    warnings: list = field(default_factory=list)

    # Filled in by later pipeline stages.
    geo_code: str = ""
    geo_name: str = ""
    geo_flag: str = ""
    score: float = 0.0
    verified: bool | None = None
    latency_ms: int | None = None
    name: str = ""

    @property
    def endpoint(self) -> str:
        """``host:port`` — the unit the liveness probe works on."""
        return f"{self.host}:{self.port}"

    def as_dict(self) -> dict:
        return {
            "protocol": self.protocol,
            "host": self.host,
            "port": self.port,
            "network": self.network,
            "security": self.security,
            "sni": self.sni,
            "remark": self.remark,
            "name": self.name,
            "source": self.source,
            "score": round(self.score, 2),
            "verified": self.verified,
            "latency_ms": self.latency_ms,
            "warnings": list(self.warnings),
            "country": self.geo_code,
            "fingerprint": self.fingerprint,
        }


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _b64decode(value: str) -> bytes | None:
    """Tolerant Base64 decode (padding, whitespace, URL-safe alphabet)."""

    if not value:
        return None
    compact = re.sub(r"\s+", "", value)
    if len(compact) < 4 or not _B64_BODY_RE.match(compact):
        return None
    compact += "=" * ((-len(compact)) % 4)
    for decoder in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            return decoder(compact, validate=False)
        except (binascii.Error, ValueError):
            continue
    return None


def _b64decode_text(value: str) -> str | None:
    decoded = _b64decode(value)
    if decoded is None:
        return None
    try:
        return decoded.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _b64encode_text(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def _split_uri(uri: str) -> tuple[str, str, str, str]:
    """Split ``scheme://netloc?query#fragment`` without urllib's surprises.

    ``urlsplit`` refuses to treat some real-world payloads as URLs (and it
    percent-decodes nothing for us), so the split is done by hand.

    The fragment is taken from the **last** ``#``, not the first one: free
    feeds publish Trojan passwords that legitimately contain a ``#``
    (``trojan://8r<[9'l6hAO#8ZQi@1.2.3.4:443#remark``), and splitting on the
    first ``#`` would throw the whole config away.  Losing part of a remark
    that itself contains a ``#`` is harmless — the pipeline replaces every
    remark with its own name anyway.
    """

    scheme, _, rest = uri.partition("://")
    fragment = ""
    if "#" in rest:
        rest, _, fragment = rest.rpartition("#")
    query = ""
    if "?" in rest:
        rest, _, query = rest.partition("?")
    return scheme.strip().lower(), rest, query, fragment


def _split_userinfo(netloc: str) -> tuple[str, str]:
    """Split ``user:pass@host:port`` on the *last* ``@``."""

    userinfo, sep, hostport = netloc.rpartition("@")
    if not sep:
        return "", netloc
    return userinfo, hostport


def _split_hostport(hostport: str) -> tuple[str, int]:
    hostport = hostport.strip()
    if not hostport:
        return "", 0
    if hostport.startswith("["):  # IPv6 literal
        host, _, tail = hostport.partition("]")
        host = host.lstrip("[")
        port_part = tail.lstrip(":")
    elif ":" in hostport:
        host, _, port_part = hostport.rpartition(":")
    else:
        return hostport.lower(), 0
    try:
        port = int(port_part)
    except ValueError:
        return host.lower(), 0
    if not 0 < port < 65536:
        return host.lower(), 0
    return host.lower(), port


def _params(query: str) -> dict:
    out: dict[str, str] = {}
    for key, value in parse_qsl(query, keep_blank_values=True):
        out.setdefault(key.strip().lower(), value)
    return out


def _valid_uuid(value: str) -> bool:
    try:
        _uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return True


def _clean_remark(value: str) -> str:
    """Make a remark safe to embed back into a URI fragment."""

    value = unquote(value or "").replace("\r", " ").replace("\n", " ")
    value = value.split("#", 1)[0]
    value = re.sub(r"\s+", " ", value).strip()
    return value[:120]


# ---------------------------------------------------------------------------
# Stream level extraction
# ---------------------------------------------------------------------------


def looks_like_error_page(text: str) -> bool:
    """Detect HTML / CDN error bodies that are served with HTTP 200."""

    head = text[:800].lstrip().lower()
    if head.startswith("<!doctype html") or head.startswith("<html"):
        return True
    markers = (
        "error 1027",
        "error 1015",
        "rate limited",
        "just a moment",
        "attention required",
        "cloudflare",
        "<title>404",
    )
    return any(marker in head for marker in markers)


def normalize_line(raw: str) -> str | None:
    """Clean one subscription line, or return ``None`` when unusable."""

    if not raw:
        return None
    value = raw.replace("\ufeff", "").strip()
    if not value or value.startswith("#"):
        return None
    if _HTMLISH_RE.search(value):
        value = html.unescape(value)
    value = value.strip("\"'` \t")
    value = value.replace("\r", "").replace("\n", "").replace("\t", "")
    value = value.strip()
    if not value:
        return None
    if not _URI_RE.match(value):
        # Some sources prefix each line with a bullet, an index or other
        # junk ("3) vless://…").  Keep everything from the first protocol
        # marker onwards, but never touch the inside of the URI — remarks
        # legitimately contain spaces.
        match = _URI_RE.search(value)
        if not match:
            return None
        value = value[match.start() :]
    return value


def extract_uris(text: str) -> list[str]:
    """Split a subscription body into individual URIs.

    Handles plain newline separated lists *and* the "everything on one line"
    streams some providers publish, by splitting on the lookahead of the next
    ``scheme://`` marker.
    """

    if not text:
        return []
    pieces: list[str] = []
    matches = list(_URI_RE.finditer(text))
    if not matches:
        return []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        chunk = text[match.start() : end]
        # A URI never contains a raw newline, so anything after the first
        # line break belongs to the next (non-config) line.  Concatenated
        # streams have no line breaks at all and are left untouched.
        chunk = chunk.split("\n", 1)[0]
        chunk = chunk.strip().rstrip(",;")
        if chunk:
            pieces.append(chunk)
    return pieces


def decode_body(content: str, *, allow_double: bool = True) -> str:
    """Return plain text for a subscription body that may be Base64 encoded.

    Sources publish plain text, single Base64 or — occasionally — double
    Base64.  The heuristics are deliberately conservative: content that
    already starts with a protocol marker or a ``#`` metadata header is
    returned untouched.
    """

    if not content:
        return ""
    stripped = content.lstrip("\ufeff \t\r\n")
    if not stripped:
        return ""
    if stripped.startswith("#") or _URI_RE.match(stripped):
        return content
    decoded = _b64decode_text(stripped)
    if decoded is None:
        return content
    inner = decoded.strip()
    if not inner:
        return content
    if allow_double:
        again = _b64decode_text(inner)
        if again and (again.lstrip().startswith("#") or _URI_RE.match(again.lstrip())):
            return again
    if inner.startswith("#") or _URI_RE.match(inner):
        return inner
    # Decoded into something that is not a subscription at all.
    return content


# ---------------------------------------------------------------------------
# Per protocol parsers
# ---------------------------------------------------------------------------


def _finish(
    cfg: Config,
    *,
    query: str = "",
    fragment: str = "",
    fingerprint_extra: tuple = (),
) -> Config:
    cfg.params = _params(query)
    if fragment:
        remark = _clean_remark(fragment)
        if remark:
            cfg.remark = remark
    if not cfg.remark:
        cfg.remark = cfg.host or "unnamed"

    network = (cfg.params.get("type") or cfg.params.get("network") or cfg.network or "tcp")
    cfg.network = network.lower()
    if cfg.network not in KNOWN_NETWORKS:
        cfg.warnings.append("unknown-network")
    security = (cfg.params.get("security") or cfg.security or "none").lower()
    if security in ("reality-tls",):
        security = "reality"
    cfg.security = security
    if cfg.security not in KNOWN_SECURITY:
        cfg.warnings.append("unknown-security")
    sni = cfg.params.get("sni") or cfg.params.get("host") or cfg.sni
    if cfg.security in ("tls", "reality", "xtls") and not sni:
        sni = cfg.host
    cfg.sni = sni.lower() if sni else ""

    if cfg.params.get("allowinsecure") in ("1", "true", "yes"):
        cfg.warnings.append("allow-insecure")
    if cfg.params.get("tls") == "none" and cfg.security in ("tls", "reality"):
        cfg.warnings.append("tls-disabled")

    parts = [
        cfg.scheme,
        cfg.host,
        str(cfg.port),
        cfg.secret,
        cfg.network,
        cfg.security,
        cfg.sni,
        cfg.params.get("path", ""),
        cfg.params.get("flow", ""),
        cfg.params.get("pbk", ""),
        cfg.ss_method,
    ]
    cfg.fingerprint = "|".join(parts) + "|" + "|".join(fingerprint_extra)
    return cfg


def _parse_vless(netloc: str, query: str, fragment: str) -> Config | None:
    userinfo, hostport = _split_userinfo(netloc)
    host, port = _split_hostport(hostport)
    secret = unquote(userinfo)
    if not host or not port or not secret:
        return None
    if not _valid_uuid(secret):
        return None
    return _finish(
        Config(
            raw="",
            scheme="vless",
            protocol="vless",
            host=host,
            port=port,
            secret=secret,
            network="tcp",
            security="none",
            remark="",
        ),
        query=query,
        fragment=fragment,
    )


def _parse_trojan(netloc: str, query: str, fragment: str) -> Config | None:
    userinfo, hostport = _split_userinfo(netloc)
    host, port = _split_hostport(hostport)
    secret = unquote(userinfo)
    if not host or not port or not secret:
        return None
    return _finish(
        Config(
            raw="",
            scheme="trojan",
            protocol="trojan",
            host=host,
            port=port,
            secret=secret,
            network="tcp",
            security="tls",
            remark="",
        ),
        query=query,
        fragment=fragment,
    )


def _parse_vmess(payload: str, fragment: str) -> Config | None:
    decoded = _b64decode_text(payload)
    data: dict | None = None
    query = ""
    if decoded:
        text = decoded.strip()
        if text.startswith("{"):
            try:
                loaded = json.loads(text)
            except (ValueError, TypeError):
                loaded = None
            if isinstance(loaded, dict):
                data = loaded
        elif ("=" in text and "&" in text) or text.startswith("remarks="):
            query = text
    if data is None and query:
        data = {k: v for k, v in parse_qsl(query, keep_blank_values=True)}
    if data is None:
        return None

    host = str(data.get("add") or data.get("host") or "").strip()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        port = int(str(data.get("port") or 0))
    except (TypeError, ValueError):
        port = 0
    secret = str(data.get("id") or data.get("uuid") or "").strip()
    if not host or not port or not 0 < port < 65536:
        return None
    if not _valid_uuid(secret):
        return None

    net = str(data.get("net") or "tcp").lower()
    tls = str(data.get("tls") or "").lower()
    security = "tls" if tls in ("tls", "true", "1") else "none"
    sni = str(data.get("sni") or data.get("host") or "").strip()

    cfg = Config(
        raw="",
        scheme="vmess",
        protocol="vmess",
        host=host.lower(),
        port=port,
        secret=secret,
        network=net,
        security=security,
        sni=sni.lower(),
        remark=str(data.get("ps") or data.get("remarks") or "").strip(),
        ss_method=str(data.get("scy") or "auto"),
    )
    cfg.vmess_json = data
    try:
        version = int(str(data.get("v", 2)))
    except (TypeError, ValueError):
        version = 2
    if version < 2:
        cfg.legacy = True
        cfg.warnings.append("legacy-vmess")

    query_pairs = [
        ("type", str(data.get("type") or "")),
        ("path", str(data.get("path") or "")),
        ("host", sni),
        ("flow", str(data.get("flow") or "")),
    ]
    query = "&".join(f"{k}={v}" for k, v in query_pairs if v)
    finished = _finish(cfg, query=query, fragment=fragment)
    if data.get("ps") and fragment:
        # An explicit fragment always wins over the embedded ``ps``.
        finished.remark = _clean_remark(fragment) or finished.remark
    return finished


def _parse_ss(netloc: str, query: str, fragment: str) -> Config | None:
    userinfo, hostport = _split_userinfo(netloc)
    method = password = ""
    body = ""
    if userinfo:
        decoded = _b64decode_text(unquote(userinfo)) or unquote(userinfo)
        if ":" in decoded:
            method, _, password = decoded.partition(":")
        host, port = _split_hostport(hostport)
    else:
        # Legacy form: ss://BASE64(method:password@host:port)#remark
        decoded = _b64decode_text(netloc)
        if not decoded or "@" not in decoded:
            return None
        creds, _, hostport = decoded.rpartition("@")
        if ":" not in creds:
            return None
        method, _, password = creds.partition(":")
        host, port = _split_hostport(hostport)
        body = decoded
    method = method.strip().lower()
    password = password.strip()
    if not host or not port or not password or not method:
        return None
    cfg = Config(
        raw="",
        scheme="ss",
        protocol="ss",
        host=host,
        port=port,
        secret=password,
        network="tcp",
        security="none",
        ss_method=method,
        ss_body=body,
        remark="",
    )
    if method not in KNOWN_SS_METHODS:
        cfg.warnings.append("unknown-ss-method")
    finished = _finish(cfg, query=query, fragment=fragment)
    if finished.params.get("plugin"):
        finished.warnings.append("plugin")
    return finished


def _parse_tuic(netloc: str, query: str, fragment: str) -> Config | None:
    userinfo, hostport = _split_userinfo(netloc)
    host, port = _split_hostport(hostport)
    if not host or not port or not userinfo:
        return None
    if ":" in userinfo:
        secret, _, password = userinfo.partition(":")
    else:
        secret, password = userinfo, ""
    secret = unquote(secret)
    if not _valid_uuid(secret):
        return None
    cfg = Config(
        raw="",
        scheme="tuic",
        protocol="tuic",
        host=host,
        port=port,
        secret=secret,
        network="udp",
        security="tls",
        remark="",
    )
    cfg.params = {"password": password}
    finished = _finish(cfg, query=query, fragment=fragment)
    finished.params["password"] = password
    return finished


def _parse_hysteria(netloc: str, query: str, fragment: str, scheme: str) -> Config | None:
    userinfo, hostport = _split_userinfo(netloc)
    host, port = _split_hostport(hostport)
    params = _params(query)
    secret = unquote(userinfo) or params.get("auth", "")
    if not host or not port or not secret:
        return None
    cfg = Config(
        raw="",
        scheme=scheme,
        protocol=scheme,
        host=host,
        port=port,
        secret=secret,
        network="udp",
        security="tls",
        remark="",
    )
    return _finish(cfg, query=query, fragment=fragment)


def _parse_wireguard(netloc: str, query: str, fragment: str) -> Config | None:
    userinfo, hostport = _split_userinfo(netloc)
    host, port = _split_hostport(hostport)
    params = _params(query)
    public_key = unquote(userinfo) or params.get("publickey", "")
    if not host or not port or not public_key:
        return None
    cfg = Config(
        raw="",
        scheme="wireguard",
        protocol="wireguard",
        host=host,
        port=port,
        secret=params.get("privatekey", ""),
        network="udp",
        security="none",
        remark="",
    )
    return _finish(cfg, query=query, fragment=fragment, fingerprint_extra=(public_key,))


PARSERS = {
    "vless": lambda n, q, f, s: _parse_vless(n, q, f),
    "vmess": lambda n, q, f, s: _parse_vmess(n, f),
    "trojan": lambda n, q, f, s: _parse_trojan(n, q, f),
    "ss": lambda n, q, f, s: _parse_ss(n, q, f),
    "tuic": lambda n, q, f, s: _parse_tuic(n, q, f),
    "hy2": lambda n, q, f, s: _parse_hysteria(n, q, f, "hy2"),
    "hysteria": lambda n, q, f, s: _parse_hysteria(n, q, f, "hysteria"),
    "wireguard": lambda n, q, f, s: _parse_wireguard(n, q, f),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_uri(uri: str, *, source: str = "") -> Config | None:
    """Parse and validate a single subscription URI.

    Returns ``None`` for anything that is not a usable config — a broken
    Base64 blob, a VMess entry without a UUID, an out-of-range port, …
    """

    cleaned = normalize_line(uri)
    if not cleaned:
        return None
    scheme, netloc, query, fragment = _split_uri(cleaned)
    protocol = SCHEME_ALIASES.get(scheme)
    if not protocol:
        return None
    parser = PARSERS.get(protocol)
    if parser is None:  # pragma: no cover - registry is exhaustive
        return None
    try:
        cfg = parser(netloc, query, fragment, scheme)
    except Exception:  # never let one malformed line kill the run
        return None
    if cfg is None:
        return None
    cfg.raw = cleaned
    cfg.source = source
    return cfg


def parse_many(text: str, *, source: str = "") -> list[Config]:
    """Parse a whole subscription body (plain, Base64 or double Base64)."""

    body = decode_body(text)
    configs: list[Config] = []
    for chunk in extract_uris(body):
        cfg = parse_uri(chunk, source=source)
        if cfg is not None:
            configs.append(cfg)
    return configs


def rename(uri: str, remark: str, *, protocol: str = "") -> str:
    """Return ``uri`` with its display name replaced by ``remark``.

    Base64 VMess entries carry their name inside the encoded JSON, so simply
    appending ``#name`` (what most aggregators do) leaves the *client*
    showing the old name.  The ``ps`` field is rewritten and re-encoded
    instead.
    """

    remark = _clean_remark(remark)
    if not uri:
        return uri
    scheme, _, _ = uri.partition("://")
    # rsplit, so a '#' inside the credential is not mistaken for a remark
    base = uri.rsplit("#", 1)[0]
    if scheme.lower() == "vmess":
        payload = uri.partition("://")[2].rsplit("#", 1)[0]
        decoded = _b64decode_text(payload)
        if decoded and decoded.strip().startswith("{"):
            try:
                data = json.loads(decoded)
            except (ValueError, TypeError):
                data = None
            if isinstance(data, dict):
                data["ps"] = remark
                return f"vmess://{_b64encode_text(json.dumps(data, ensure_ascii=False))}"
        if decoded:
            pairs = [(k, v) for k, v in parse_qsl(decoded, keep_blank_values=True)]
            replaced = False
            out = []
            for key, value in pairs:
                if key in ("remarks", "ps"):
                    out.append((key, remark))
                    replaced = True
                else:
                    out.append((key, value))
            if not replaced:
                out.append(("remarks", remark))
            from urllib.parse import urlencode

            return f"vmess://{_b64encode_text(urlencode(out))}"
    return f"{base}#{remark}"
