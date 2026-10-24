"""澎湃新闻 (thepaper.cn) tag pages — Next.js pages with embedded JSON."""
from __future__ import annotations

import re

from ..util import SHANGHAI, next_data, walk
from .base import Article, Entry, Source, escape, page_meta, parse_date, pick_largest, readability_content, soup_of

DETAIL = "https://www.thepaper.cn/newsDetail_forward_{}"


def _pick_pic(d: dict) -> str | None:
    for k in ("pic", "sharePic", "smallPic", "appHeadPic"):
        v = d.get(k)
        if isinstance(v, str) and v.startswith("http"):
            return v
    return None


def _date(d: dict):
    for k in ("pubTimeLong", "publishTime", "pubTime"):
        v = d.get(k)
        when = parse_date(v, default_tz=SHANGHAI) if v else None
        if when:
            return when
    return None


class ThePaperTag(Source):
    language = "zh-CN"
    img_proxy_hosts = ("thepaper.cn",)  # images refuse requests coming from other sites

    def __init__(self, id: str, tag_id: str, title: str, description: str = ""):
        self.id, self.tag_id = id, tag_id
        self.home = f"https://www.thepaper.cn/tag/{tag_id}"
        self.title, self.description = title, description or title
        self.icon = "https://www.thepaper.cn/favicon.ico"

    def fetch_list(self, http) -> list[Entry]:
        html, final = http.text(self.home, headers=self.headers)
        data = next_data(html) or {}
        try:
            items = data["props"]["pageProps"]["data"]["data"]["list"]
        except (KeyError, TypeError):
            items = [d for d in walk(data) if d.get("contId") and d.get("name")]
        entries: list[Entry] = []
        for d in items or []:
            if not isinstance(d, dict) or not d.get("contId") or not d.get("name"):
                continue
            link = d.get("link") if d.get("forwardType") not in (None, "0", 0) and d.get("link") else \
                DETAIL.format(d["contId"])
            entries.append(Entry(link=link, title=d["name"].strip(), date=_date(d), thumb=_pick_pic(d),
                                 summary=d.get("summary") or ""))
        if not entries:
            soup = soup_of(html)
            for a in soup.select("a[href*='newsDetail_forward_']"):
                m = re.search(r"newsDetail_forward_(\d+)", a["href"])
                t = a.get_text(" ", strip=True)
                if m and t:
                    entries.append(Entry(link=DETAIL.format(m.group(1)), title=t))
        return entries

    def fetch_article(self, http, entry: Entry) -> Article:
        html, final = http.text(entry.link, headers=self.headers)
        data = next_data(html) or {}
        detail = None
        try:
            detail = data["props"]["pageProps"]["detailData"]["contentDetail"]
        except (KeyError, TypeError):
            for d in walk(data):
                c = d.get("content")
                if isinstance(c, str) and "<" in c and d.get("name"):
                    if detail is None or len(c) > len(detail.get("content", "")):
                        detail = d
        art = Article()
        content = ""
        if isinstance(detail, dict):
            content = detail.get("content") or ""
            art.title = (detail.get("name") or "").strip()
            art.date = _date(detail)
            art.thumb = _pick_pic(detail)
            art.author = detail.get("author") or ""
            for v in detail.get("videoDTOList") or detail.get("videos") or []:
                if not isinstance(v, dict):
                    continue
                src = v.get("hdurl") or v.get("url") or v.get("fhdUrl") or v.get("sdurl")
                if isinstance(src, str) and src.startswith("http"):
                    poster = v.get("coverUrl") or art.thumb or ""
                    content = f'<p><video src="{escape(src)}" poster="{escape(poster)}" controls></video></p>' + content
                    break
        if len(re.sub(r"<[^>]+>", "", content)) < 50:
            soup = soup_of(html)
            node = pick_largest(soup, ["[class*='cententWrap']", "[class*='contentWrap']", "[class*='news_txt']"])
            fb = str(node) if node is not None else readability_content(html)
            if len(fb) > len(content):
                content = fb
        meta = page_meta(html)
        art.title = art.title or entry.title or meta["title"]
        art.thumb = art.thumb or entry.thumb or meta["image"]
        art.date = art.date or entry.date or meta["date"]
        art.content = self.clean(content, final)
        return art
