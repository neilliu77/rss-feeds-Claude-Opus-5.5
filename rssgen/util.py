"""Small helpers: dates, embedded-JSON extraction, tree walking."""
from __future__ import annotations

import datetime as dt
import json
import re
from typing import Any, Iterator
from zoneinfo import ZoneInfo

from dateutil import parser as _dparser

UTC = dt.timezone.utc
SHANGHAI = ZoneInfo("Asia/Shanghai")


def now_utc() -> dt.datetime:
    return dt.datetime.now(UTC).replace(microsecond=0)


def parse_date(value: Any, default_tz=UTC) -> dt.datetime | None:
    """Parse epoch seconds/ms, ISO strings, RFC-822 strings or Chinese dates into aware UTC."""
    if value is None or value == "" or value is False:
        return None
    if isinstance(value, dt.datetime):
        d = value
    elif isinstance(value, (int, float)) or (isinstance(value, str) and re.fullmatch(r"\s*\d{9,13}(\.\d+)?\s*", value)):
        v = float(value)
        if v > 1e11:  # milliseconds
            v /= 1000.0
        if v < 1e8:
            return None
        return dt.datetime.fromtimestamp(v, UTC)
    else:
        s = str(value).strip()
        s = re.sub(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", r"\1-\2-\3 ", s)
        s = s.replace("/", "-") if re.match(r"^\d{4}/\d{1,2}/\d{1,2}", s) else s
        try:
            d = _dparser.parse(s)
        except (ValueError, OverflowError, TypeError):
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=default_tz)
    try:
        d = d.astimezone(UTC)
    except (OverflowError, ValueError):
        return None
    if d.year < 1995 or d > now_utc() + dt.timedelta(days=2):
        return None
    return d.replace(microsecond=0)


def iso(d: dt.datetime | None) -> str | None:
    return d.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if d else None


def from_iso(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return parse_date(s)


def walk(obj: Any) -> Iterator[dict]:
    """Yield every dict inside a JSON-like structure, in document order."""
    stack = [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            yield o
            stack.extend(reversed(list(o.values())))
        elif isinstance(o, list):
            stack.extend(reversed(o))


_NEXT_RE = re.compile(r'<script[^>]*\bid=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', re.S | re.I)


def next_data(html: str) -> dict | None:
    m = _NEXT_RE.search(html)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def json_after(text: str, marker: str) -> Any:
    """Decode the JSON value that follows ``marker`` and an optional '=' (e.g. window.__INITIAL_STATE__)."""
    start = 0
    while True:
        i = text.find(marker, start)
        if i < 0:
            return None
        k = i + len(marker)
        while k < len(text) and text[k] in " \t\r\n=:":
            k += 1
        if k < len(text) and text[k] in "{[":
            obj = _raw_decode(text, k)
            if obj is not None:
                return obj
        start = i + len(marker)


def _raw_decode(text: str, k: int) -> Any:
    dec = json.JSONDecoder()
    try:
        return dec.raw_decode(text, k)[0]
    except json.JSONDecodeError:
        pass
    end = text.find("</script>", k)
    chunk = text[k:end if end > 0 else None]
    chunk = re.sub(r"(?<=[:\[,])\s*undefined\s*(?=[,}\]])", "null", chunk)
    try:
        return dec.raw_decode(chunk)[0]
    except json.JSONDecodeError:
        return None


def ld_json(html: str) -> list:
    """Return all parsed <script type="application/ld+json"> blocks."""
    out = []
    for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            out.append(json.loads(m.group(1).strip()))
        except json.JSONDecodeError:
            continue
    return out


def first(*values):
    for v in values:
        if v:
            return v
    return None
