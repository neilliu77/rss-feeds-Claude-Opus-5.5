"""RSS 2.0 output (full HTML in <description>, Media-RSS thumbnail) and the per-feed JSON cache."""
from __future__ import annotations

import email.utils
import json
import os
from dataclasses import asdict, dataclass, field

from lxml import etree

from .htmlclean import xml_safe
from .util import from_iso

NS_ATOM = "http://www.w3.org/2005/Atom"
NS_MEDIA = "http://search.yahoo.com/mrss/"
NS_DC = "http://purl.org/dc/elements/1.1/"
NSMAP = {"atom": NS_ATOM, "media": NS_MEDIA, "dc": NS_DC}

# WebSub hub announced in every feed. Readers such as Inoreader subscribe to it and then receive new
# articles as soon as we ping the hub (see rssgen/websub.py), instead of waiting for their next poll.
HUBS = ("https://pubsubhubbub.appspot.com/",)


def feed_base_url() -> str:
    """Public base URL of the repository files (the feed addresses people subscribe to)."""
    base = os.environ.get("FEED_BASE_URL")
    if base:
        return base.rstrip("/") + "/"
    repo = os.environ.get("GITHUB_REPOSITORY", "neilliu77/rss-feeds-Claude-Opus-5.5")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/"


@dataclass
class Item:
    link: str
    title: str
    content: str
    date: str | None = None        # ISO-8601 UTC
    first_seen: str | None = None  # ISO-8601 UTC
    author: str = ""
    thumb: str | None = None
    categories: list[str] = field(default_factory=list)
    partial: bool = False          # True when only a summary could be fetched

    def sort_key(self):
        return (self.date or self.first_seen or "", self.first_seen or "")


class Cache:
    def __init__(self, path: str):
        self.path = path
        self.items: dict[str, Item] = {}
        self.failures: dict[str, dict] = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            for d in raw.get("items", []):
                known = {k: v for k, v in d.items() if k in Item.__dataclass_fields__}
                it = Item(**known)
                self.items[it.link] = it
            self.failures = raw.get("failures", {})

    def sorted_items(self) -> list[Item]:
        return sorted(self.items.values(), key=lambda i: i.sort_key(), reverse=True)

    def prune(self, keep: int) -> None:
        keepers = self.sorted_items()[:keep]
        self.items = {i.link: i for i in keepers}
        # forget links that are no longer on the list page after many attempts
        self.failures = {k: v for k, v in self.failures.items()
                         if (v.get("n", 0) if isinstance(v, dict) else v) < 50}

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        data = {"items": [asdict(i) for i in self.sorted_items()],
                "failures": dict(sorted(self.failures.items()))}
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, self.path)


def _rfc822(iso: str | None) -> str | None:
    d = from_iso(iso)
    return email.utils.format_datetime(d, usegmt=True) if d else None


def _sub(parent, tag, text=None, **attrs):
    el = etree.SubElement(parent, tag, **attrs)
    if text is not None:
        el.text = xml_safe(str(text))
    return el


def build_rss(*, title: str, link: str, description: str, language: str, self_url: str,
              items: list[Item], image: str | None = None) -> bytes:
    rss = etree.Element("rss", version="2.0", nsmap=NSMAP)
    ch = etree.SubElement(rss, "channel")
    _sub(ch, "title", title)
    _sub(ch, "link", link)
    _sub(ch, "description", description or title)
    _sub(ch, "language", language)
    _sub(ch, f"{{{NS_ATOM}}}link", href=self_url, rel="self", type="application/rss+xml")
    for hub in HUBS:
        _sub(ch, f"{{{NS_ATOM}}}link", href=hub, rel="hub")
    _sub(ch, "generator", "rssgen (GitHub Actions)")
    newest = max((i.date or i.first_seen or "" for i in items), default="")
    if newest:
        _sub(ch, "lastBuildDate", _rfc822(newest))
    if image:
        img = _sub(ch, "image")
        _sub(img, "url", image)
        _sub(img, "title", title)
        _sub(img, "link", link)
    for it in items:
        el = _sub(ch, "item")
        _sub(el, "title", it.title)
        _sub(el, "link", it.link)
        _sub(el, "guid", it.link, isPermaLink="true")
        pub = _rfc822(it.date or it.first_seen)
        if pub:
            _sub(el, "pubDate", pub)
        if it.author:
            _sub(el, f"{{{NS_DC}}}creator", it.author)
        for c in it.categories:
            _sub(el, "category", c)
        desc = etree.SubElement(el, "description")
        desc.text = etree.CDATA(xml_safe(it.content).replace("]]>", "]]&gt;"))
        if it.thumb:
            _sub(el, f"{{{NS_MEDIA}}}thumbnail", url=it.thumb)
    return etree.tostring(rss, xml_declaration=True, encoding="UTF-8", pretty_print=True)
