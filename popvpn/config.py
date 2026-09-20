"""Configuration loading.

The project deliberately ships **without third-party runtime dependencies**,
so instead of pulling in PyYAML this module implements the small YAML subset
that ``config.yaml`` uses:

* nested mappings (indentation based)
* scalar lists (``- item``) and inline lists (``[a, b]``)
* ``#`` comments, quoted strings, ``true/false/null``, ints and floats

Every key can also be overridden with an environment variable named
``POPVPN_<SECTION>_<KEY>`` (upper case, dots replaced by underscores), which
is what the GitHub Actions workflow uses.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

__all__ = ["Config", "ConfigError", "load_yaml_subset", "DEFAULTS"]


class ConfigError(ValueError):
    """Raised for malformed configuration files."""


# ---------------------------------------------------------------------------
# YAML subset
# ---------------------------------------------------------------------------


def _strip_comment(line: str) -> str:
    in_single = in_double = False
    for index, char in enumerate(line):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif (
            char == "#"
            and not in_single
            and not in_double
            and (index == 0 or line[index - 1] in " \t")
        ):
            return line[:index]
    return line


def _split_top_level(text: str, sep: str = ",") -> list[str]:
    parts: list[str] = []
    depth = 0
    in_single = in_double = False
    current: list[str] = []
    for char in text:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        if not in_single and not in_double:
            if char in "[{":
                depth += 1
            elif char in "]}":
                depth -= 1
            elif char == sep and depth == 0:
                parts.append("".join(current))
                current = []
                continue
        current.append(char)
    if current:
        parts.append("".join(current))
    return [part.strip() for part in parts if part.strip() != ""]


_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?$")


def _parse_scalar(text: str):
    text = text.strip()
    if text == "":
        return None
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in _split_top_level(inner)]
    lowered = text.lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    if lowered in ("null", "~", "none"):
        return None
    if _INT_RE.match(text):
        return int(text)
    if _FLOAT_RE.match(text):
        return float(text)
    return text


def _tokenize(text: str) -> list[tuple[int, str]]:
    tokens: list[tuple[int, str]] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise ConfigError(f"line {lineno}: tabs cannot be used for indentation")
        stripped = _strip_comment(raw).rstrip()
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        tokens.append((indent, stripped.strip()))
    return tokens


def _build(tokens: list[tuple[int, str]], index: int, indent: int):
    if index >= len(tokens):
        return None, index
    if tokens[index][1].startswith("-"):
        return _build_sequence(tokens, index, indent)
    return _build_mapping(tokens, index, indent)


def _build_sequence(tokens: list[tuple[int, str]], index: int, indent: int):
    items: list = []
    while index < len(tokens):
        token_indent, content = tokens[index]
        if token_indent < indent:
            break
        if not content.startswith("-"):
            break
        body = content[1:].strip()
        index += 1
        if ":" in body and body[:1] not in ("\"", "'"):
            raise ConfigError(
                "sequences of mappings are not supported by the built-in YAML "
                f"reader, got: {body!r}"
            )
        items.append(_parse_scalar(body))
    return items, index


def _build_mapping(tokens: list[tuple[int, str]], index: int, indent: int):
    mapping: dict = {}
    while index < len(tokens):
        token_indent, content = tokens[index]
        if token_indent < indent:
            break
        if token_indent > indent:
            raise ConfigError(f"unexpected indentation at: {content!r}")
        key, sep, value = content.partition(":")
        if not sep:
            raise ConfigError(f"expected 'key: value', got {content!r}")
        key = key.strip().strip("\"'")
        value = value.strip()
        index += 1
        if value:
            mapping[key] = _parse_scalar(value)
            continue
        if index < len(tokens) and tokens[index][0] > indent:
            child, index = _build(tokens, index, tokens[index][0])
            mapping[key] = child
        elif (
            index < len(tokens)
            and tokens[index][0] == indent
            and tokens[index][1].startswith("-")
        ):
            child, index = _build(tokens, index, indent)
            mapping[key] = child
        else:
            mapping[key] = None
    return mapping, index


def load_yaml_subset(text: str) -> dict:
    """Parse the supported YAML subset into a ``dict``."""

    tokens = _tokenize(text)
    if not tokens:
        return {}
    value, index = _build(tokens, 0, tokens[0][0])
    if index != len(tokens):  # pragma: no cover - defensive
        raise ConfigError(f"unparsed trailing content at token {index}")
    if not isinstance(value, dict):
        raise ConfigError("the top level of a config file must be a mapping")
    return value


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

DEFAULTS: dict = {
    "profile.title": "POPVPN X",
    "profile.brand": "POPVPN",
    "profile.update_interval": 1,
    "profile.total": 10737418240000000,
    "profile.expire": 2546249531,
    "profile.profile_web_page_url": "",
    "profile.support_url": "",
    "profile.client_types": "",
    "profile.announce": "",
    "profile.repo": "",
    "profile.branch": "main",
    "sources.file": "links.txt",
    "sources.max_failures": 3,
    "sources.revive_after_hours": 6,
    "sources.state_file": "state/sources.json",
    "fetch.workers": 12,
    "fetch.connect_timeout": 10,
    "fetch.read_timeout": 45,
    "fetch.retries": 3,
    "fetch.backoff": 1.6,
    "fetch.jitter": 0.35,
    "fetch.max_bytes": 26214400,
    "fetch.use_cache": True,
    "fetch.use_stale_on_error": True,
    "fetch.cache_ttl": 900,
    "fetch.cache_dir": ".cache/http",
    "fetch.user_agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    ),
    "parsing.protocols": ["vless", "vmess", "trojan", "ss", "tuic", "hy2", "wireguard"],
    "parsing.split_concatenated": True,
    "parsing.allow_double_base64": True,
    "naming.template": "{brand} {index} {flag} {country} {protocol} {transport}",
    "naming.index_width": 4,
    "naming.separator": "|",
    "naming.max_length": 60,
    "naming.unique": True,
    "geo.unknown_label": "GLOBAL",
    "scoring.enabled": True,
    "scoring.sort": "score",
    "scoring.shuffle_within_country": False,
    "security.drop_insecure": False,
    "security.drop_private_hosts": False,
    "security.drop_legacy_vmess": False,
    "security.max_warnings": 99,
    "probe.mode": "off",
    "probe.workers": 96,
    "probe.timeout": 4.0,
    "probe.tls": False,
    "probe.max_endpoints": 4000,
    "probe.cache_ttl": 3600,
    "probe.state_file": "state/probe_cache.json",
    "probe.drop_dead": False,
    "limits.max_configs": 12000,
    "limits.per_protocol": 0,
    "limits.best_count": 100,
    "limits.clash_max": 3000,
    "limits.dashboard_configs": 400,
    "outputs.dir": "outputs",
    "outputs.root_files": True,
    "outputs.by_protocol": True,
    "outputs.by_country": True,
    "outputs.clash": True,
    "outputs.singbox": True,
    "outputs.dashboard": "dashboard",
    "outputs.readme": "README.md",
    "outputs.history_file": "state/history.json",
    "outputs.history_keep": 240,
    "outputs.sparkline": "outputs/history.svg",
    "notify.enabled": True,
    "notify.min_drop_percent": 40,
    "quiet": False,
}


_ENV_PREFIX = "POPVPN_"


def _coerce(value: str, sample):
    if isinstance(sample, bool):
        return value.strip().lower() in ("1", "true", "yes", "on")
    if isinstance(sample, int):
        try:
            return int(value)
        except ValueError:
            return sample
    if isinstance(sample, float):
        try:
            return float(value)
        except ValueError:
            return sample
    if isinstance(sample, list):
        return [part.strip() for part in re.split(r"[,\s]+", value.strip()) if part.strip()]
    return value


class Config:
    """Dot-path access over the merged defaults / file / environment."""

    def __init__(self, data: dict | None = None) -> None:
        self.data = data or {}

    # -- construction ----------------------------------------------------
    @classmethod
    def load(cls, path: str | Path | None = None, *, overrides: dict | None = None) -> "Config":
        data: dict = {}
        if path is not None:
            file_path = Path(path)
            if file_path.exists():
                data = load_yaml_subset(file_path.read_text(encoding="utf-8"))
            elif Path(path).name != "config.yaml":
                raise ConfigError(f"config file not found: {path}")
        if overrides:
            data = _deep_merge(data, overrides)
        return cls(data)

    # -- access ----------------------------------------------------------
    def get(self, path: str, default=None):
        node = self.data
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                node = None
                break
            node = node[part]
        if node is None:
            node = DEFAULTS.get(path, default)
        env_key = _ENV_PREFIX + path.upper().replace(".", "_")
        env_value = os.environ.get(env_key)
        if env_value is not None and env_value != "":
            sample = node if node is not None else DEFAULTS.get(path)
            return _coerce(env_value, sample)
        return node if node is not None else default

    def section(self, name: str) -> dict:
        raw = self.data.get(name, {}) if isinstance(self.data, dict) else {}
        merged = dict(DEFAULTS)
        out: dict = {}
        prefix = name + "."
        for key, sample in merged.items():
            if key.startswith(prefix):
                out[key[len(prefix) :]] = self.get(key, sample)
        if isinstance(raw, dict):
            for key in raw:
                out.setdefault(key, raw[key])
        return out

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"Config({self.data!r})"


def _deep_merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out
