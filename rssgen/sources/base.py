"""Common source interface plus shared extraction helpers."""
from __future__ import annotations

import datetime as dt
import logging
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from ..htmlclean import absolute, clean_html, count_images, escape, first_image, proxied, text_of
from ..util import first, iso, ld_json, parse_date

log = logging.getLogger("rssgen")


@dataclass
class Entry:
    """One article as seen on a list page."""
    link: str
    title: str = ""
    date: dt.datetime | None = None
    thumb: str | None = None
    summary: str = ""
    author: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class Article:
    """Details fetched from the article page."""
    title: str = ""
    content: str = ""          # cleaned HTML
    date: dt.datetime | None = None
    thumb: str | None = None
    author: str = ""
    categories: list[str] = field(default_factory=list)


class Source:
    id: str = ""
    title: str = ""
    home: str = ""
    description: str = ""
    language: str = "zh-CN"
    accept_language: str = "zh-CN,zh;q=0.9,en;q=0.6"
    list_limit: int = 30       # how many list entries to look at per run
    keep: int = 30             # how many items the feed keeps
    img_proxy_hosts: tuple[str, ...] = ()
    prepend_cover: bool = True  # put the thumbnail on top when the article body has no picture
    icon: str | None = None

    # --- to implement -------------------------------------------------
    def fetch_list(self, http) -> list[Entry]:
        raise NotImplementedError

    def fetch_article(self, http, entry: Entry) -> Article:
        raise NotImplementedError

    # --- helpers --------------------------------------------------------
    @property
    def headers(self) -> dict:
        return {"Accept-Language": self.accept_language}

    def clean(self, fragment, base_url: str, **kw) -> str:
        return clean_html(fragment, base_url, proxy_hosts=self.img_proxy_hosts, **kw)

    def build_content(self, entry: Entry, art: Article) -> tuple[str, str | None]:
        content = art.content or ""
        thumb = first(entry.thumb, art.thumb, first_image(content))
        thumb = proxied(absolute(entry.link, thumb), self.img_proxy_hosts, thumb=True) if thumb else None
        head = content[:3000]
        if thumb and self.prepend_cover and count_images(head) == 0 and "<iframe" not in head \
                and "<video" not in head:
            content = f'<p><img src="{escape(thumb)}" alt=""/></p>\n' + content
        return content, thumb

    def partial_content(self, entry: Entry) -> str:
        summary = entry.summary or ""
        if summary and "<" not in summary:
            summary = f"<p>{escape(summary)}</p>"
        return (summary + f'<p><a href="{escape(entry.link)}">（暂时无法抓取全文，点此阅读原文）</a></p>')


# ---------------------------------------------------------------- page helpers
def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def meta(soup: BeautifulSoup, *names: str) -> str | None:
    for n in names:
        tag = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n}) \
            or soup.find("meta", attrs={"itemprop": n})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None


def page_meta(html: str, soup: BeautifulSoup | None = None) -> dict:
    """Title / image / date / author from OpenGraph, standard meta tags and JSON-LD."""
    soup = soup or soup_of(html)
    info = {
        "title": meta(soup, "og:title", "twitter:title"),
        "image": meta(soup, "og:image", "og:image:url", "twitter:image", "twitter:image:src"),
        "date": parse_date(meta(soup, "article:published_time", "og:release_date", "pubdate", "publishdate",
                                "datePublished", "parsely-pub-date", "sailthru.date", "date")),
        "author": meta(soup, "author", "article:author", "og:article:author"),
        "description": meta(soup, "og:description", "description"),
    }
    for block in ld_json(html):
        for node in (block if isinstance(block, list) else block.get("@graph", [block]) if isinstance(block, dict) else []):
            if not isinstance(node, dict):
                continue
            info["date"] = info["date"] or parse_date(node.get("datePublished"))
            if not info["image"]:
                img = node.get("image")
                if isinstance(img, dict):
                    img = img.get("url")
                if isinstance(img, list) and img:
                    img = img[0].get("url") if isinstance(img[0], dict) else img[0]
                if isinstance(img, str):
                    info["image"] = img
            if not info["author"]:
                au = node.get("author")
                if isinstance(au, list) and au:
                    au = au[0]
                if isinstance(au, dict):
                    au = au.get("name")
                if isinstance(au, str):
                    info["author"] = au
    if not info["title"] and soup.title:
        info["title"] = soup.title.get_text(strip=True)
    return info


def readability_content(html: str) -> str:
    """Generic main-content extraction used as a last resort."""
    try:
        from readability import Document
        return Document(html).summary(html_partial=True)
    except Exception as e:  # noqa
        log.debug("readability failed: %s", e)
        return ""


def pick_largest(soup: BeautifulSoup, selectors: list[str]):
    """Return the element with most text among those matching the selectors (first selector wins ties)."""
    best, best_len = None, 0
    for sel in selectors:
        for el in soup.select(sel):
            n = len(el.get_text(strip=True))
            if n > best_len * 1.2:
                best, best_len = el, n
        if best is not None and best_len > 200:
            return best
    return best


def strip_title(text: str, suffixes: list[str]) -> str:
    t = (text or "").strip()
    for s in suffixes:
        t = re.sub(re.escape(s) + r"\s*$", "", t).strip()
    return t


__all__ = ["Entry", "Article", "Source", "soup_of", "meta", "page_meta", "readability_content", "pick_largest",
           "strip_title", "absolute", "text_of", "first", "iso", "parse_date", "escape", "log"]
