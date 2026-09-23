"""On-disk HTTP cache.

Subscription sources are large and rate limited; caching bodies together with
their ``ETag`` / ``Last-Modified`` lets a run finish in seconds when nothing
changed, and keeps the runner polite towards the upstream hosts.

The cache lives outside git (``.cache/``) and is restored between runs by
``actions/cache`` in the workflow.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path


class HttpCache:
    def __init__(
        self, directory: str | Path, ttl: int = 900, enabled: bool = True, *, writable: bool = True
    ) -> None:
        self.directory = Path(directory)
        self.ttl = int(ttl)
        self.enabled = enabled
        self.writable = writable
        self.hits = 0
        self.misses = 0
        if self.enabled and self.writable:
            self.directory.mkdir(parents=True, exist_ok=True)

    # -- helpers ---------------------------------------------------------
    def _key(self, url: str) -> str:
        return hashlib.sha1(url.encode("utf-8")).hexdigest()

    def _meta_path(self, url: str) -> Path:
        return self.directory / f"{self._key(url)}.json"

    def _body_path(self, url: str) -> Path:
        return self.directory / f"{self._key(url)}.body"

    # -- API -------------------------------------------------------------
    def get(self, url: str) -> tuple[str, dict] | None:
        """Return ``(body, meta)`` when a fresh entry exists."""

        if not self.enabled:
            return None
        meta_path = self._meta_path(url)
        if not meta_path.exists():
            self.misses += 1
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.misses += 1
            return None
        age = time.time() - float(meta.get("fetched_at", 0))
        if age > self.ttl:
            self.misses += 1
            return None
        body_path = self._body_path(url)
        if not body_path.exists():
            self.misses += 1
            return None
        self.hits += 1
        return body_path.read_text(encoding="utf-8", errors="replace"), meta

    def validators(self, url: str) -> dict:
        """``ETag`` / ``Last-Modified`` of the last stored response."""

        if not self.enabled:
            return {}
        meta_path = self._meta_path(url)
        if not meta_path.exists():
            return {}
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return {
            "etag": meta.get("etag", ""),
            "last_modified": meta.get("last_modified", ""),
        }

    def stored_body(self, url: str) -> str | None:
        """Body of the last stored response, even when the TTL expired."""

        body_path = self._body_path(url)
        if not body_path.exists():
            return None
        try:
            return body_path.read_text(encoding="utf-8", errors="replace")
        except OSError:  # pragma: no cover - defensive
            return None

    def put(self, url: str, body: str, headers: dict | None = None) -> None:
        if not self.enabled or not self.writable:
            return
        headers = headers or {}
        meta = {
            "url": url,
            "fetched_at": time.time(),
            "etag": headers.get("etag", ""),
            "last_modified": headers.get("last-modified", ""),
            "bytes": len(body.encode("utf-8")),
        }
        try:
            self._body_path(url).write_text(body, encoding="utf-8")
            self._meta_path(url).write_text(
                json.dumps(meta, ensure_ascii=False), encoding="utf-8"
            )
        except OSError:  # pragma: no cover - disk full etc.
            pass

    def touch(self, url: str) -> None:
        """Refresh the timestamp after a ``304 Not Modified``."""

        if not self.enabled or not self.writable:
            return
        meta_path = self._meta_path(url)
        if not meta_path.exists():
            return
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["fetched_at"] = time.time()
            meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        except (OSError, ValueError):  # pragma: no cover - defensive
            pass

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {
            "enabled": self.enabled,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 3) if total else 0.0,
        }
