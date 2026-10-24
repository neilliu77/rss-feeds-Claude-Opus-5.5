"""游民星空 (gamersky.com) review hub: https://www.gamersky.com/review/

The hub page has one tab per platform; the "全部评测" tab (node 20915) lists every review and
hands-on preview with thumbnail, summary, author, time and score. Articles live at
/news/<yyyymm>/<id>.shtml; long ones may be split into <id>_2.shtml, <id>_3.shtml ...
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..util import SHANGHAI
from .base import Article, Entry, Source, escape, page_meta, parse_date, readability_content, soup_of

ALL_REVIEWS_NODE = "20915"


class GamerskyReviews(Source):
    id = "gamersky-review"
    title = "游民星空 · 游戏评测"
    home = "https://www.gamersky.com/review/"
    description = "游民星空「游戏评测」栏目：评测与试玩报告全文"
    language = "zh-CN"
    img_proxy_hosts = ("gamersky.com",)  # images refuse requests coming from other sites
    icon = "https://www.gamersky.com/favicon.ico"

    def fetch_list(self, http) -> list[Entry]:
        html, final = http.text(self.home, headers=self.headers)
        soup = soup_of(html)
        ul = soup.select_one(f'ul.pictxt[data-nodeid="{ALL_REVIEWS_NODE}"]') or soup.select_one("ul.pictxt")
        entries: list[Entry] = []
        for li in ul.select(":scope > li") if ul else []:
            a = li.select_one(".tit a[href]") or li.select_one("a[href]")
            if not a:
                continue
            link = urljoin(final, a["href"])
            title = (a.get("title") or a.get_text(" ", strip=True)).strip()
            img = li.select_one(".img img")
            txt = li.select_one(".txt")
            tm = li.select_one(".time")
            tag = li.select_one(".tag")
            num = li.select_one(".pc .num")
            score = num.get_text(strip=True) if num else ""
            entries.append(Entry(
                link=link, title=title,
                thumb=urljoin(final, img["src"]) if img and img.get("src") else None,
                summary=txt.get_text(" ", strip=True) if txt else "",
                date=parse_date(tm.get_text(strip=True), default_tz=SHANGHAI) if tm else None,
                author=re.sub(r"^作者[:：]\s*", "", tag.get_text(strip=True)) if tag else "",
                extra={"score": score if re.fullmatch(r"\d+(\.\d+)?", score) else ""}))
        return entries

    def _body(self, soup: BeautifulSoup):
        node = soup.select_one(".Mid_L .MidLcon") or soup.select_one(".MidLcon")
        if node is None:
            return None
        for t in node.select("p.appGameBuyCardIframe, #pe100_page_contentpage, .gs_comm_content_bot_fun"):
            t.decompose()
        for t in node.select("div.title1, div.title2"):
            t.name = "h3"
        return node

    def fetch_article(self, http, entry: Entry) -> Article:
        html, final = http.text(entry.link, headers=self.headers, referer=self.home)
        soup = soup_of(html)
        art = Article()
        h1 = soup.select_one(".Top2 h1.tit") or soup.find("h1")
        art.title = entry.title or (h1.get_text(" ", strip=True) if h1 else "")
        tm = soup.select_one(".Top2 .time")
        art.date = (parse_date(tm.get_text(strip=True), default_tz=SHANGHAI) if tm else None) or entry.date
        art.author = entry.author
        top = soup.select_one(".Top[style]")
        m = re.search(r"url\(['\"]?([^)'\"]+)", top["style"]) if top else None
        cover = urljoin(final, m.group(1)) if m else None

        # collect the continuation pages (<id>_2.shtml ...) listed in the pager, before the pager is removed
        base_id = re.search(r"/(\d+)\.shtml", final)
        pages = []
        if base_id:
            for a in soup.select("#pe100_page_contentpage a[href], .page_css a[href]"):
                pm = re.search(rf"/{base_id.group(1)}_(\d+)\.shtml", a["href"])
                if pm:
                    pages.append((int(pm.group(1)), urljoin(final, a["href"])))
        pages = [u for _, u in sorted(set(pages))][:15]

        parts = []
        if entry.extra.get("score"):
            parts.append(f"<p><strong>游民评分：{escape(entry.extra['score'])}</strong></p>")
        if cover:
            parts.append(f'<p><img src="{escape(cover)}" alt=""/></p>')
        body = self._body(soup)
        parts.append(str(body) if body is not None else readability_content(html))
        for url in pages:
            try:
                more_html, _ = http.text(url, headers=self.headers, referer=entry.link)
            except Exception:  # noqa - keep what we have
                break
            more = self._body(soup_of(more_html))
            if more is not None:
                parts.append(str(more))
        if body is None:
            meta = page_meta(html, soup)
            art.title = art.title or meta["title"] or ""
        art.thumb = cover
        art.content = self.clean("\n".join(parts), final)
        return art
