from __future__ import annotations

import pytest

from popvpn.config import DEFAULTS, Config, ConfigError, load_yaml_subset


def test_nested_mapping():
    data = load_yaml_subset(
        """
        profile:
          title: "My VPN"
          update_interval: 2
        fetch:
          workers: 8
        """
    )
    assert data == {"profile": {"title": "My VPN", "update_interval": 2}, "fetch": {"workers": 8}}


def test_comments_and_blank_lines():
    data = load_yaml_subset(
        """
        # leading comment
        key: value   # trailing comment

        # another
        other: 42
        """
    )
    assert data == {"key": "value", "other": 42}


def test_hash_inside_quotes_is_kept():
    data = load_yaml_subset('template: "{brand} # {index}"')
    assert data["template"] == "{brand} # {index}"


def test_scalars():
    data = load_yaml_subset(
        """
        text: plain string
        quoted: "with: colon"
        single: 'single'
        yes: true
        no: false
        nothing: null
        tilde: ~
        integer: -12
        number: 1.5
        exponent: 1e3
        """
    )
    assert data["text"] == "plain string"
    assert data["quoted"] == "with: colon"
    assert data["single"] == "single"
    assert data["yes"] is True
    assert data["no"] is False
    assert data["nothing"] is None
    assert data["tilde"] is None
    assert data["integer"] == -12
    assert data["number"] == 1.5
    assert data["exponent"] == 1000.0


def test_inline_and_block_lists():
    data = load_yaml_subset(
        """
        inline: [a, b, c]
        block:
          - one
          - two
        numbers: [1, 2]
        """
    )
    assert data["inline"] == ["a", "b", "c"]
    assert data["block"] == ["one", "two"]
    assert data["numbers"] == [1, 2]


def test_sequence_at_key_indent():
    data = load_yaml_subset(
        """
        items:
        - a
        - b
        """
    )
    assert data == {"items": ["a", "b"]}


def test_tabs_are_rejected():
    with pytest.raises(ConfigError):
        load_yaml_subset("key:\n\tvalue: 1\n")


def test_missing_colon_is_rejected():
    with pytest.raises(ConfigError):
        load_yaml_subset("just a line\n")


def test_mapping_sequence_rejected_with_message():
    with pytest.raises(ConfigError, match="sequences of mappings"):
        load_yaml_subset("items:\n  - name: x\n")


def test_shipped_config_yaml_loads():
    cfg = Config.load("config.yaml")
    assert cfg.get("profile.title") == "POPVPN X"
    assert cfg.get("profile.brand") == "POPVPN"
    assert isinstance(cfg.get("parsing.protocols"), list)
    assert "vless" in cfg.get("parsing.protocols")
    assert cfg.get("naming.separator") == "|"
    assert cfg.get("probe.mode") == "tcp"
    assert cfg.get("probe.require_verified") is True
    assert cfg.get("security.drop_weak_credentials") is True
    assert cfg.get("fetch.max_bytes") == 26214400


def test_every_default_is_reachable_from_shipped_config():
    cfg = Config.load("config.yaml")
    for key in DEFAULTS:
        assert cfg.get(key) is not None, key


def test_env_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("POPVPN_PROFILE_TITLE", "ENV TITLE")
    monkeypatch.setenv("POPVPN_FETCH_WORKERS", "3")
    monkeypatch.setenv("POPVPN_PROBE_MODE", "tcp")
    monkeypatch.setenv("POPVPN_OUTPUTS_CLASH", "false")
    cfg = Config.load("config.yaml")
    assert cfg.get("profile.title") == "ENV TITLE"
    assert cfg.get("fetch.workers") == 3
    assert cfg.get("probe.mode") == "tcp"
    assert cfg.get("outputs.clash") is False


def test_env_override_list(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("POPVPN_PARSING_PROTOCOLS", "vless,trojan")
    cfg = Config.load("config.yaml")
    assert cfg.get("parsing.protocols") == ["vless", "trojan"]


def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        Config.load(tmp_path / "nope.yaml")


def test_overrides_win_over_file(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("profile:\n  title: file\n", encoding="utf-8")
    cfg = Config.load(path, overrides={"profile": {"title": "override"}})
    assert cfg.get("profile.title") == "override"


def test_section_returns_full_defaults():
    cfg = Config.load("config.yaml")
    section = cfg.section("profile")
    assert section["title"] == "POPVPN X"
    assert section["update_interval"] == 1
