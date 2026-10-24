"""WordPress sites: REST API first, then the built-in feed, then plain HTML."""
from __future__ import annotations

import html as _html
import re

from lxml import etree

from .base import Article, Entry, Source, page_meta, parse_date, pick_largest, readability_content, soup_of


class WordPressSite(Source):
    language = "zh-CN"
    REMOVE = ("#ez-toc-container", ".ez-toc-container", ".sharedaddy", ".jp-relatedposts", ".post-share",
              ".wp-block-buttons", ".yarpp-related", ".addtoany_share_save_container")

    def __init__(self, id: str, home: str, title: str, description: str = "", per_page: int = 20):
        self.id, self.home = id, home.rstrip("/") + "/"
        self.title, self.description = title, description or title
        self.per_page = per_page
        self.icon = None
        self._full: dict[str, Article] = {}

    # ------------------------------------------------------------- list
    def fetch_list(self, http) -> list[Entry]:
        errors = []
        try:
            entries = self._from_api(http)
            if entries:
                return entries
        except Exception as e:  # noqa
            errors.append(f"api: {e}")
        try:
            entries = self._from_feed(http)
            if entries:
                return entries
        except Exception as e:  # noqa
            errors.append(f"feed: {e}")
        try:
            entries = self._from_html(http)
            if entries:
                return entries
        except Exception as e:  # noqa
            errors.append(f"html: {e}")
        raise RuntimeError("; ".join(errors) or "no posts found")

    def _from_api(self, http) -> list[Entry]:
        posts = http.json(self.home + "wp-json/wp/v2/posts", params={"per_page": self.per_page, "_embed": "1"},
                          headers={**self.headers, "Accept": "application/json"})
        entries = []
        for p in posts:
            link = p.get("link")
            title = _html.unescape(re.sub(r"<[^>]+>", "", (p.get("title") or {}).get("rendered", ""))).strip()
            content = (p.get("content") or {}).get("rendered", "")
            date = parse_date(p.get("date_gmt") + "Z" if p.get("date_gmt") else p.get("date"))
            emb = p.get("_embedded") or {}
            thumb = None
            fm = emb.get("wp:featuredmedia") or []
            if fm and isinstance(fm[0], dict):
                sizes = (fm[0].get("media_details") or {}).get("sizes") or {}
                pick = sizes.get("medium_large") or sizes.get("large") or sizes.get("full") or {}
                thumb = pick.get("source_url") or fm[0].get("source_url")
            author = ""
            au = emb.get("author") or []
            if au and isinstance(au[0], dict):
                author = au[0].get("name", "")
            cats = []
            for group in emb.get("wp:term") or []:
                for term in group or []:
                    if isinstance(term, dict) and term.get("taxonomy") == "category":
                        cats.append(_html.unescape(term.get("name", "")))
            if link and title:
                self._full[link] = Article(title=title, content=content, date=date, thumb=thumb, author=author,
                                           categories=cats)
                entries.append(Entry(link=link, title=title, date=date, thumb=thumb, author=author))
        return entries

    def _from_feed(self, http) -> list[Entry]:
        r = http.get(self.home + "feed/", headers=self.headers)
        root = etree.fromstring(r.content, parser=etree.XMLParser(recover=True))
        ns = {"content": "http://purl.org/rss/1.0/modules/content/", "dc": "http://purl.org/dc/elements/1.1/"}
        entries = []
        for it in root.iter("item"):
            link = (it.findtext("link") or "").strip()
            title = (it.findtext("title") or "").strip()
            full = it.findtext("content:encoded", namespaces=ns) or ""
            date = parse_date(it.findtext("pubDate"))
            author = it.findtext("dc:creator", namespaces=ns) or ""
            if link and title:
                if len(re.sub(r"<[^>]+>", "", full)) > 500:
                    self._full[link] = Article(title=title, content=full, date=date, author=author)
                entries.append(Entry(link=link, title=title, date=date, author=author,
                                     summary=it.findtext("description") or ""))
        return entries

    def _from_html(self, http) -> list[Entry]:
        html, final = http.text(self.home, headers=self.headers)
        soup = soup_of(html)
        entries, seen = [], set()
        for a in soup.select(".entry-title a[href], h2 a[href], h3 a[href], h4 a[href]"):
            href = a["href"]
            if not href.startswith(self.home) or href in seen or "/category/" in href or "/tag/" in href:
                continue
            seen.add(href)
            entries.append(Entry(link=href, title=a.get_text(" ", strip=True)))
        return entries

    # ---------------------------------------------------------- article
    def fetch_article(self, http, entry: Entry) -> Article:
        cached = self._full.get(entry.link)
        if cached and len(re.sub(r"<[^>]+>", "", cached.content)) > 200:
            return Article(title=cached.title, content=self.clean(cached.content, entry.link, remove=self.REMOVE),
                           date=cached.date, thumb=cached.thumb, author=cached.author, categories=cached.categories)
        html, final = http.text(entry.link, headers=self.headers)
        soup = soup_of(html)
        node = pick_largest(soup, [".entry-content", ".post-content", ".single-content", "article .content",
                                   ".mg-blog-post-box article", "article"])
        content = str(node) if node is not None else readability_content(html)
        meta = page_meta(html, soup)
        return Article(title=meta["title"] or entry.title,
                       content=self.clean(content, final, remove=self.REMOVE),
                       date=meta["date"] or entry.date, thumb=meta["image"], author=meta["author"] or "")
