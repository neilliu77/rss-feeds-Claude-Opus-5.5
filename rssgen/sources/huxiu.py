"""虎嗅 (huxiu.com) collections — list from the site's own JSON API, full text from the article page."""
from __future__ import annotations

import re

from ..util import SHANGHAI
from .base import Article, Entry, Source, escape, page_meta, parse_date, pick_largest, readability_content, soup_of

ARTICLE = "https://www.huxiu.com/article/{}.html"
API = "https://api-article.huxiu.com/web/collection/articleList"


def _plain_pic(url: str | None) -> str | None:
    """Huxiu image URLs carry processing suffixes like ?imageView2/...|imageMogr2/...; keep a sane size."""
    if not url:
        return None
    base = url.split("?")[0]
    return base + "?imageView2/2/w/1000/format/jpg/interlace/1/q/85"


class HuxiuCollection(Source):
    language = "zh-CN"
    img_proxy_hosts = ("huxiucdn.com", "huxiu.com")  # images refuse requests coming from other sites

    def __init__(self, id: str, collection_id: str, title: str, description: str = ""):
        self.id, self.collection_id = id, collection_id
        self.home = f"https://www.huxiu.com/collection/{collection_id}.html"
        self.title, self.description = title, description or title
        self.icon = "https://www.huxiu.com/favicon.ico"

    def fetch_list(self, http) -> list[Entry]:
        entries: list[Entry] = []
        try:
            data = http.json(API, method="POST",
                             data={"platform": "www", "collection_id": self.collection_id, "page": "1"},
                             headers={**self.headers, "Origin": "https://www.huxiu.com",
                                      "Accept": "application/json, text/plain, */*"},
                             referer="https://www.huxiu.com/")
            for d in (data.get("data") or {}).get("datalist") or []:
                aid, title = d.get("aid"), d.get("title")
                if not aid or not title:
                    continue
                author = (d.get("author_info") or d.get("user_info") or {}).get("username") or ""
                entries.append(Entry(link=ARTICLE.format(aid), title=title.replace("​", "").strip(),
                                     thumb=_plain_pic(d.get("pic_path")), summary=d.get("summary") or "",
                                     author=author, date=parse_date(d.get("dateline"), default_tz=SHANGHAI)))
        except Exception:  # noqa - fall back to the HTML page below
            entries = []
        if entries:
            return entries
        html, final = http.text(self.home, headers=self.headers)
        soup = soup_of(html)
        seen = set()
        for a in soup.select("a[href*='/article/']"):
            m = re.search(r"/article/(\d+)\.html", a["href"])
            t = (a.get("title") or a.get_text(" ", strip=True) or "").strip()
            if m and t and m.group(1) not in seen:
                seen.add(m.group(1))
                entries.append(Entry(link=ARTICLE.format(m.group(1)), title=t))
        return entries

    def fetch_article(self, http, entry: Entry) -> Article:
        html, final = http.text(entry.link, headers=self.headers, referer=self.home)
        soup = soup_of(html)
        meta = page_meta(html, soup)
        node = soup.select_one(".article__content") or pick_largest(
            soup, ["#article-content", ".article-content-wrap", "[class*='article__content']",
                   "[class*='article-content']"])
        content = str(node) if node is not None else readability_content(html)
        top = soup.select_one(".article__top-img img")
        cover = top.get("src") if top else None
        if cover:
            content = f'<p><img src="{escape(_plain_pic(cover))}" alt=""/></p>' + content
        h1 = soup.select_one("h1.article__title") or soup.find("h1")
        title = (h1.get_text(" ", strip=True) if h1 else "") or entry.title or meta["title"] or ""
        title = re.sub(r"-虎嗅网$", "", title).strip()
        return Article(title=entry.title or title,
                       content=self.clean(content, final, remove=(".text-remarks-empty",)),
                       date=meta["date"] or entry.date, thumb=_plain_pic(cover) or meta["image"],
                       author=entry.author or "")
