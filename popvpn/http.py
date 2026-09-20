"""HTTP layer.

Pure ``urllib`` implementation so the pipeline needs no third-party packages.
It provides:

* retries with exponential backoff + jitter (429 / 5xx / network errors)
* transparent ``gzip`` / ``deflate`` decoding
* a hard response size cap (a runaway source must not fill the runner disk)
* polite per-host spacing and a browser ``User-Agent``
* optional conditional requests (``ETag`` / ``If-Modified-Since``) via :mod:`popvpn.cache`
* a thread pool for fetching many sources concurrently
"""

from __future__ import annotations

import gzip
import io
import json
import random
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Iterable

RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504, 520, 521, 522, 524}


class HttpError(Exception):
    """Raised when a fetch ultimately fails."""


@dataclass
class FetchResult:
    url: str
    status: int = 0
    text: str = ""
    ok: bool = False
    error: str = ""
    elapsed_ms: int = 0
    size: int = 0
    from_cache: bool = False
    headers: dict = field(default_factory=dict)


@dataclass
class HttpSettings:
    connect_timeout: float = 10.0
    read_timeout: float = 45.0
    retries: int = 3
    backoff: float = 1.6
    jitter: float = 0.35
    max_bytes: int = 26_214_400
    user_agent: str = "POPVPN-X/2.0"
    verify_tls: bool = True


def _ssl_context(settings: HttpSettings) -> ssl.SSLContext:
    context = ssl.create_default_context()
    if not settings.verify_tls:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


def _decode_body(raw: bytes, encoding: str) -> bytes:
    encoding = (encoding or "").lower()
    if "gzip" in encoding:
        try:
            return gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        except (OSError, EOFError, zlib.error):
            return raw
    if "deflate" in encoding:
        try:
            return zlib.decompress(raw)
        except zlib.error:
            try:
                return zlib.decompress(raw, -zlib.MAX_WBITS)
            except zlib.error:
                return raw
    return raw


def _decode_text(raw: bytes, content_type: str) -> str:
    charset = ""
    for part in (content_type or "").split(";"):
        part = part.strip()
        if part.lower().startswith("charset="):
            charset = part.split("=", 1)[1].strip("\"' ")
    for candidate in (charset, "utf-8", "utf-8-sig", "cp1252"):
        if not candidate:
            continue
        try:
            return raw.decode(candidate)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", errors="replace")


def fetch(
    url: str,
    settings: HttpSettings | None = None,
    *,
    etag: str = "",
    last_modified: str = "",
    on_progress: Callable[[str], None] | None = None,
) -> FetchResult:
    """Download ``url`` returning a :class:`FetchResult` (never raises)."""

    settings = settings or HttpSettings()
    url = url.strip()
    if not url:
        return FetchResult(url=url, error="empty url")

    started = time.monotonic()
    attempt = 0
    last_error = "unknown"
    status = 0

    while attempt <= max(0, settings.retries):
        attempt += 1
        headers = {
            "User-Agent": settings.user_agent,
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Cache-Control": "no-cache",
            "Connection": "close",
        }
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(
                request,
                timeout=settings.read_timeout,
                context=_ssl_context(settings),
            ) as response:
                status = getattr(response, "status", 200)
                raw = response.read(settings.max_bytes + 1)
                final_headers = {k.lower(): v for k, v in response.headers.items()}
                if len(raw) > settings.max_bytes:
                    return FetchResult(
                        url=url,
                        status=status,
                        error=f"response larger than {settings.max_bytes} bytes",
                        elapsed_ms=int((time.monotonic() - started) * 1000),
                    )
                body = _decode_body(raw, final_headers.get("content-encoding", ""))
                text = _decode_text(body, final_headers.get("content-type", ""))
                if on_progress:
                    on_progress(url)
                return FetchResult(
                    url=url,
                    status=status,
                    text=text,
                    ok=True,
                    size=len(raw),
                    elapsed_ms=int((time.monotonic() - started) * 1000),
                    headers=final_headers,
                )
        except urllib.error.HTTPError as exc:
            status = exc.code
            last_error = f"HTTP {exc.code}"
            if exc.code == 304:
                return FetchResult(
                    url=url,
                    status=304,
                    ok=True,
                    from_cache=True,
                    elapsed_ms=int((time.monotonic() - started) * 1000),
                )
            if exc.code not in RETRYABLE_STATUS:
                break
        except (urllib.error.URLError, socket.timeout, TimeoutError, ssl.SSLError) as exc:
            last_error = f"{type(exc).__name__}: {getattr(exc, 'reason', exc)}"
        except (OSError, ValueError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"

        if attempt > settings.retries:
            break
        delay = settings.backoff ** attempt
        delay += random.uniform(0, settings.jitter)
        time.sleep(min(delay, 20))

    return FetchResult(
        url=url,
        status=status,
        ok=False,
        error=last_error,
        elapsed_ms=int((time.monotonic() - started) * 1000),
    )


def post_json(url: str, payload: dict, settings: HttpSettings | None = None) -> FetchResult:
    """POST a JSON payload — used by the notification hooks."""

    settings = settings or HttpSettings()
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": settings.user_agent,
        },
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(
            request, timeout=settings.read_timeout, context=_ssl_context(settings)
        ) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
            return FetchResult(
                url=url,
                status=getattr(response, "status", 200),
                text=body,
                ok=True,
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )
    except Exception as exc:  # notifications must never break a run
        return FetchResult(
            url=url,
            ok=False,
            error=f"{type(exc).__name__}: {exc}",
            elapsed_ms=int((time.monotonic() - started) * 1000),
        )


def fetch_many(
    urls: Iterable[str],
    settings: HttpSettings | None = None,
    *,
    workers: int = 8,
    etags: dict | None = None,
) -> dict[str, FetchResult]:
    """Fetch every URL concurrently, keyed by URL (order independent)."""

    urls = [u for u in dict.fromkeys(urls) if u]
    if not urls:
        return {}
    settings = settings or HttpSettings()
    etags = etags or {}
    results: dict[str, FetchResult] = {}
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(urls)))) as pool:
        futures = {
            pool.submit(
                fetch,
                url,
                settings,
                etag=(etags.get(url) or {}).get("etag", ""),
                last_modified=(etags.get(url) or {}).get("last_modified", ""),
            ): url
            for url in urls
        }
        for future in as_completed(futures):
            url = futures[future]
            try:
                results[url] = future.result()
            except Exception as exc:  # pragma: no cover - defensive
                results[url] = FetchResult(url=url, ok=False, error=f"{type(exc).__name__}: {exc}")
    return results


def host_of(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower()
