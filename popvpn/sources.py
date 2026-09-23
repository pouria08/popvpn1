"""Source list handling + per-source health tracking.

``links.txt`` accepts one URL per line.  Blank lines and ``#`` comments are
ignored, and a URL can carry inline annotations:

    https://example.com/sub.txt   # name=Barry weight=2 country=DE

Health is persisted in ``state/sources.json`` so a source that starts failing
is skipped automatically (and re-tried after a cool-down instead of burning
every run on a dead host).
"""

from __future__ import annotations

import contextlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

_ANNOTATION_KEYS = ("name", "weight", "country", "disabled", "note")


@dataclass
class Source:
    url: str
    name: str = ""
    weight: int = 1
    country: str = ""
    note: str = ""
    enabled: bool = True
    # Filled in per run.
    ok: bool = False
    error: str = ""
    elapsed_ms: int = 0
    found: int = 0
    from_cache: bool = False
    status: int = 0

    @property
    def host(self) -> str:
        from urllib.parse import urlsplit

        return (urlsplit(self.url).hostname or "").lower()


def parse_links(text: str) -> list[Source]:
    """Parse ``links.txt`` content into :class:`Source` objects."""

    sources: list[Source] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        url, _, annotation = line.partition("#")
        url = url.strip()
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            continue
        if url in seen:
            continue
        seen.add(url)
        source = Source(url=url)
        for token in annotation.split():
            key, sep, value = token.partition("=")
            key = key.strip().lower()
            if not sep or key not in _ANNOTATION_KEYS:
                continue
            value = value.strip()
            if key == "weight":
                with contextlib.suppress(ValueError):
                    source.weight = max(0, int(value))
            elif key == "disabled":
                source.enabled = value.lower() not in ("1", "true", "yes", "on")
            elif key == "name":
                source.name = value.replace("_", " ")
            else:
                setattr(source, key, value)
        if not source.name:
            source.name = source.host or url
        sources.append(source)
    return sources


def load_sources(path: str | Path) -> list[Source]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"source list not found: {path}")
    return parse_links(file_path.read_text(encoding="utf-8"))


class SourceHealth:
    """Persistent success/latency tracking for every known source URL."""

    def __init__(self, path: str | Path, max_failures: int = 3, revive_after_hours: float = 6):
        self.path = Path(path)
        self.max_failures = max(1, int(max_failures))
        self.revive_after_hours = float(revive_after_hours)
        self.records: dict[str, dict] = {}
        self.load()

    # -- persistence -----------------------------------------------------
    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        records = data.get("sources", data)
        if isinstance(records, dict):
            self.records = {k: v for k, v in records.items() if isinstance(v, dict)}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"updated_at": int(time.time()), "sources": self.records}
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    # -- queries ---------------------------------------------------------
    def record_for(self, url: str) -> dict:
        return self.records.setdefault(
            url,
            {
                "name": "",
                "attempts": 0,
                "successes": 0,
                "fail_streak": 0,
                "last_ok_at": 0,
                "last_fail_at": 0,
                "last_error": "",
                "last_status": 0,
                "avg_ms": 0,
                "reliability": 1.0,
                "last_configs": 0,
            },
        )

    def is_paused(self, url: str) -> bool:
        record = self.records.get(url)
        if not record:
            return False
        if record.get("fail_streak", 0) < self.max_failures:
            return False
        last = max(record.get("last_fail_at", 0), record.get("last_ok_at", 0))
        cool_down = self.revive_after_hours * 3600
        return (time.time() - last) < cool_down

    def reliability(self, url: str) -> float:
        record = self.records.get(url)
        if not record:
            return 1.0
        return float(record.get("reliability", 1.0))

    def retain(self, urls) -> int:
        """Forget health records for sources no longer present in ``links.txt``.

        Keeping an obsolete record is not useful for cooldown/reliability and
        risks showing a removed feed again in the public health report.
        Disabled sources are passed in by the caller too, so their history is
        preserved until the operator actually removes the line.
        """

        allowed = set(urls)
        before = len(self.records)
        self.records = {url: record for url, record in self.records.items() if url in allowed}
        return before - len(self.records)

    # -- updates ---------------------------------------------------------
    def record(self, source: Source) -> None:
        record = self.record_for(source.url)
        record["name"] = source.name or record.get("name", "")
        record["attempts"] = int(record.get("attempts", 0)) + 1
        if source.ok:
            record["successes"] = int(record.get("successes", 0)) + 1
            record["fail_streak"] = 0
            record["last_ok_at"] = int(time.time())
            record["last_status"] = source.status
            record["last_error"] = ""
            record["last_configs"] = source.found
            previous = float(record.get("avg_ms", 0) or 0)
            record["avg_ms"] = int(previous * 0.6 + source.elapsed_ms * 0.4)
            record["reliability"] = round(
                float(record.get("reliability", 1.0)) * 0.75 + 0.25, 4
            )
        else:
            record["fail_streak"] = int(record.get("fail_streak", 0)) + 1
            record["last_fail_at"] = int(time.time())
            record["last_error"] = source.error[:200]
            record["last_status"] = source.status
            record["last_configs"] = 0
            record["reliability"] = round(float(record.get("reliability", 1.0)) * 0.75, 4)

    def summary(self) -> list[dict]:
        out = []
        for url, record in sorted(self.records.items(), key=lambda kv: -kv[1].get("last_configs", 0)):
            attempts = max(1, int(record.get("attempts", 0)))
            out.append(
                {
                    "url": url,
                    "name": record.get("name", ""),
                    "attempts": attempts,
                    "success_rate": round(int(record.get("successes", 0)) / attempts, 3),
                    "fail_streak": int(record.get("fail_streak", 0)),
                    "last_configs": int(record.get("last_configs", 0)),
                    "avg_ms": int(record.get("avg_ms", 0)),
                    "reliability": float(record.get("reliability", 1.0)),
                    "last_error": record.get("last_error", ""),
                    "paused": self.is_paused(url),
                }
            )
        return out
