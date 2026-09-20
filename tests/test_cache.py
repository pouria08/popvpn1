from __future__ import annotations

import json
import time

from popvpn.cache import HttpCache
from popvpn.sources import Source, SourceHealth, parse_links

# ---------------------------------------------------------------------------
# HTTP cache
# ---------------------------------------------------------------------------


def test_cache_round_trip(tmp_path):
    cache = HttpCache(tmp_path / "cache", ttl=60)
    assert cache.get("https://example.com/a") is None
    cache.put("https://example.com/a", "vless://x", {"etag": "W/1", "last-modified": "Mon"})
    hit = cache.get("https://example.com/a")
    assert hit is not None
    body, meta = hit
    assert body == "vless://x"
    assert meta["etag"] == "W/1"
    assert cache.validators("https://example.com/a")["last_modified"] == "Mon"
    assert cache.stats()["hits"] == 1


def test_cache_ttl_expiry(tmp_path):
    cache = HttpCache(tmp_path / "cache", ttl=1)
    cache.put("https://example.com/b", "body", {})
    assert cache.get("https://example.com/b") is not None
    meta_path = tmp_path / "cache" / f"{cache._key('https://example.com/b')}.json"
    meta = json.loads(meta_path.read_text())
    meta["fetched_at"] = time.time() - 3600
    meta_path.write_text(json.dumps(meta))
    assert cache.get("https://example.com/b") is None
    # …but the stale body is still available for a 304 / error fallback
    assert cache.stored_body("https://example.com/b") == "body"


def test_cache_touch_refreshes_ttl(tmp_path):
    cache = HttpCache(tmp_path / "cache", ttl=60)
    cache.put("https://example.com/c", "body", {})
    meta_path = tmp_path / "cache" / f"{cache._key('https://example.com/c')}.json"
    meta = json.loads(meta_path.read_text())
    meta["fetched_at"] = time.time() - 3600
    meta_path.write_text(json.dumps(meta))
    cache.touch("https://example.com/c")
    assert cache.get("https://example.com/c") is not None


def test_cache_disabled(tmp_path):
    cache = HttpCache(tmp_path / "cache", enabled=False)
    cache.put("https://example.com/d", "body", {})
    assert cache.get("https://example.com/d") is None
    assert cache.validators("https://example.com/d") == {}


# ---------------------------------------------------------------------------
# Source list + health
# ---------------------------------------------------------------------------


def test_parse_links_with_annotations():
    text = "\n".join(
        [
            "# comment",
            "",
            "https://example.com/a.txt   # name=Alpha weight=3 country=DE",
            "https://example.com/b.txt   # disabled=true",
            "https://example.com/a.txt   # duplicate is ignored",
            "not-a-url",
            "https://example.com/c.txt",
        ]
    )
    sources = parse_links(text)
    assert [s.url for s in sources] == [
        "https://example.com/a.txt",
        "https://example.com/b.txt",
        "https://example.com/c.txt",
    ]
    assert sources[0].name == "Alpha"
    assert sources[0].weight == 3
    assert sources[0].country == "DE"
    assert sources[1].enabled is False
    assert sources[2].name == "example.com"


def test_source_host():
    assert parse_links("https://Example.com/path")[0].host == "example.com"


def test_health_pause_and_revive(tmp_path):
    health = SourceHealth(tmp_path / "sources.json", max_failures=2, revive_after_hours=1)
    url = "https://example.com/dead"
    source = Source(url=url, name="dead")
    assert health.is_paused(url) is False
    health.record(source)
    health.record(source)
    assert health.is_paused(url) is True
    assert health.reliability(url) < 1.0

    # after the cool-down the source is tried again
    record = health.records[url]
    record["last_fail_at"] = int(time.time() - 7200)
    record["last_ok_at"] = 0
    assert health.is_paused(url) is False


def test_health_success_resets_streak(tmp_path):
    health = SourceHealth(tmp_path / "sources.json", max_failures=1)
    url = "https://example.com/flaky"
    failing = Source(url=url, name="flaky")
    health.record(failing)
    assert health.is_paused(url) is True
    ok = Source(url=url, name="flaky", ok=True, elapsed_ms=120, found=10, status=200)
    health.record(ok)
    assert health.is_paused(url) is False
    assert health.records[url]["avg_ms"] > 0
    assert health.records[url]["last_configs"] == 10


def test_health_persistence(tmp_path):
    path = tmp_path / "sources.json"
    health = SourceHealth(path)
    health.record(Source(url="https://example.com/x", name="x", ok=True, found=3, elapsed_ms=50, status=200))
    health.save()
    reloaded = SourceHealth(path)
    assert reloaded.records["https://example.com/x"]["last_configs"] == 3
    summary = reloaded.summary()
    assert summary[0]["success_rate"] == 1.0
    assert summary[0]["paused"] is False


def test_health_survives_corrupt_file(tmp_path):
    path = tmp_path / "sources.json"
    path.write_text("{not json", encoding="utf-8")
    health = SourceHealth(path)
    assert health.records == {}
