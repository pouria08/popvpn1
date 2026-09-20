from __future__ import annotations

import pytest

from popvpn import geo


@pytest.mark.parametrize(
    "remark,code",
    [
        ("🇩🇪 DE-Frankfurt", "DE"),
        ("🇳🇱 NL Amsterdam", "NL"),
        ("🇮🇷 IR-Tehran-MCI", "IR"),
        ("US-East-01", "US"),
        ("IR-TEHRAN-03", "IR"),
        ("node DE2", "DE"),
        ("IT2 milano", "IT"),
        ("frankfurt hetzner relay", "DE"),
        ("istanbul turkey", "TR"),
        ("newyork city", "US"),
        ("singapore", "SG"),
        ("tehran irancell", "IR"),
        ("ashgabat", "TM"),
        ("seoul korea 01", "KR"),
        ("no country here at all", ""),
    ],
)
def test_detect(remark: str, code: str):
    assert geo.detect(remark).code == code


def test_flag_for():
    assert geo.flag_for("DE") == "🇩🇪"
    assert geo.flag_for("ir") == "🇮🇷"
    assert geo.flag_for("XYZ") == ""
    assert geo.flag_for("") == ""


def test_flag_round_trip_matches_detection():
    detected = geo.detect("🇫🇷 FR-Paris")
    assert detected.flag == geo.flag_for("FR")
    assert detected.name == "France"


def test_unknown_returns_fallback():
    fallback = geo.Geo("XX", "Nowhere", "🏳️")
    assert geo.detect("???", fallback=fallback) == fallback


def test_region_mapping():
    assert geo.detect("🇩🇪 DE").region == "EU"
    assert geo.detect("US-East").region == "NA"
    assert geo.detect("singapore").region == "AS"
    assert geo.detect("nothing").region == ""


def test_ambiguous_code_needs_digit():
    # "ID" alone is far more likely a word than Indonesia.
    assert geo.detect("node id 42").code == ""
    assert geo.detect("ID-03 node").code == "ID"


def test_country_summary():
    geos = [geo.detect("🇩🇪 DE"), geo.detect("🇩🇪 DE"), geo.detect("US-East"), geo.detect("???")]
    rows = geo.country_summary(geos)
    assert rows[0]["code"] == "DE"
    assert rows[0]["count"] == 2
    assert rows[0]["flag"] == "🇩🇪"
    assert {row["code"] for row in rows} == {"DE", "US", "?"}


def test_countries_have_valid_flags():
    for code in geo.COUNTRIES:
        assert len(code) == 2 and code.isupper()
        assert len(geo.flag_for(code)) == 2
