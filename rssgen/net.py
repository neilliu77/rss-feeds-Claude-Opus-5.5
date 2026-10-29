"""HTTP client that looks like a normal Chrome browser (TLS fingerprint included)."""
from __future__ import annotations

import logging
import random
import re
import time
from urllib.parse import urlsplit

log = logging.getLogger("rssgen")

try:
    from curl_cffi import requests as _creq
except ImportError:  # pragma: no cover - fallback for local testing
    _creq = None
import requests as _preq

DESKTOP_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")

RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504, 520, 521, 522, 524}


class FetchError(Exception):
    pass


class Http:
    def __init__(self, min_interval: float = 1.2):
        if _creq is not None:
            self.session = _creq.Session(impersonate="chrome")
        else:
            self.session = _preq.Session()
            self.session.headers["User-Agent"] = DESKTOP_UA
        self.min_interval = min_interval
        self._last_hit: dict[str, float] = {}

    def _throttle(self, url: str) -> None:
        host = urlsplit(url).hostname or ""
        wait = self._last_hit.get(host, 0) + self.min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait + random.uniform(0, 0.4))
        self._last_hit[host] = time.monotonic()

    def get(self, url: str, *, headers: dict | None = None, referer: str | None = None, params=None,
            timeout: float = 30, retries: int = 3):
        """GET with polite per-site pacing and retries on temporary errors (429, 5xx, timeouts)."""
        h = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7"}
        if referer:
            h["Referer"] = referer
        if headers:
            h.update(headers)
        last_err: Exception | None = None
        for attempt in range(retries):
            self._throttle(url)
            try:
                r = self.session.get(url, headers=h, params=params, timeout=timeout, allow_redirects=True)
            except Exception as e:  # network-level problem
                last_err = e
                log.debug("  GET %s failed (%s), attempt %d", url, e, attempt + 1)
            else:
                if r.status_code in RETRY_STATUS:
                    last_err = FetchError(f"HTTP {r.status_code} for {url}")
                elif r.status_code >= 400:
                    raise FetchError(f"HTTP {r.status_code} for {url}")
                else:
                    return r
            time.sleep(2 ** attempt * 2 + random.uniform(0, 1.5))
        raise FetchError(str(last_err))

    def text(self, url: str, **kw) -> tuple[str, str]:
        """GET a page and return (decoded_text, final_url)."""
        r = self.get(url, **kw)
        return decode_body(r.content, r.headers.get("content-type", "")), str(r.url)

    def json(self, url: str, **kw):
        return self.get(url, **kw).json()


_META_CHARSET = re.compile(rb'<meta[^>]+charset=["\']?\s*([A-Za-z0-9_\-]+)', re.I)


def decode_body(content: bytes, content_type: str = "") -> str:
    charset = None
    m = re.search(r"charset=([A-Za-z0-9_\-]+)", content_type or "", re.I)
    if m:
        charset = m.group(1)
    if not charset:
        m2 = _META_CHARSET.search(content[:4096])
        if m2:
            charset = m2.group(1).decode("ascii", "ignore")
    charset = (charset or "utf-8").lower()
    if charset in ("gb2312", "gbk"):
        charset = "gb18030"
    try:
        return content.decode(charset, errors="replace")
    except LookupError:
        return content.decode("utf-8", errors="replace")
