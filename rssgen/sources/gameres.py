"""GameRes 游资网 list pages (www.gameres.com/list/<id>).

The list mixes GameRes' own articles (/<number>.html) with links to WeChat articles (/wl?m=<hash>,
which redirect to mp.weixin.qq.com). Both are followed to get the full text.
"""
from __future__ import annotations

import datetime as dt
import re
from urllib.parse import urljoin

from ..util import SHANGHAI, now_utc
from .base import (Article, Entry, Source, page_meta, parse_date, pick_largest, readability_content, soup_of,
                   strip_title)
from .wechat import WECHAT_IMG_HOSTS, is_wechat, parse_wechat


def _mmdd_to_date(text: str):
    """'10-22' (no year) -> a date within the past year (Shanghai noon)."""
    text = text or ""
    m = re.search(r"(20\d\d)[-/.年](\d{1,2})[-/.月](\d{1,2})", text)
    if m:
        return parse_date(f"{m.group(1)}-{m.group(2)}-{m.group(3)} 12:00", default_tz=SHANGHAI)
    m = re.search(r"(?<!\d)(\d{1,2})-(\d{1,2})(?!\d)", text)
    if not m:
        return None
    now = now_utc().astimezone(SHANGHAI)
    try:
        d = dt.datetime(now.year, int(m.group(1)), int(m.group(2)), 12, 0, tzinfo=SHANGHAI)
    except ValueError:
        return None
    if d > now + dt.timedelta(days=1):
        d = d.replace(year=now.year - 1)
    return parse_date(d)


class GameResList(Source):
    language = "zh-CN"
    img_proxy_hosts = ("gameres.com",) + WECHAT_IMG_HOSTS  # both refuse images requested from other sites

    def __init__(self, id: str, list_id: str, title: str, description: str = ""):
        self.id, self.list_id = id, list_id
        self.home = f"https://www.gameres.com/list/{list_id}"
        self.title, self.description = title, description or title
        self.icon = "https://www.gameres.com/favicon.ico"

    def fetch_list(self, http) -> list[Entry]:
        html, final = http.text(self.home, headers=self.headers)
        soup = soup_of(html)
        entries: list[Entry] = []
        for item in soup.select("article.feed-item"):
            a = item.select_one("a.feed-item-title-a[href]") or item.select_one("a[href]")
            if not a:
                continue
            link = urljoin("https://www.gameres.com/", a["href"].strip())
            t = item.select_one(".feed-item-title-text")
            title = (t.get_text(" ", strip=True) if t else a.get_text(" ", strip=True)) or ""
            img = item.select_one("img.thumb") or item.select_one("img")
            thumb = urljoin("https://www.gameres.com/", img.get("src")) if img and img.get("src") else None
            s = item.select_one(".feed-item-summary")
            tm = item.select_one("time")
            entries.append(Entry(link=link, title=title.strip(), thumb=thumb,
                                 summary=s.get_text(" ", strip=True) if s else "",
                                 date=_mmdd_to_date(tm.get_text(strip=True) if tm else ""),
                                 extra={"external": bool(item.select_one(".feed-item-ext-icon"))}))
        if not entries:  # layout changed: fall back to any article-looking link
            seen = set()
            for a in soup.select("a[href]"):
                link = urljoin("https://www.gameres.com/", a["href"].strip())
                if re.match(r"^https://www\.gameres\.com/(\d+\.html|wl\?m=[0-9a-f]+)", link) and link not in seen:
                    title = a.get_text(" ", strip=True)
                    if len(title) >= 4:
                        seen.add(link)
                        entries.append(Entry(link=link, title=title))
        return entries

    def fetch_article(self, http, entry: Entry) -> Article:
        html, final = http.text(entry.link, headers=self.headers, referer=self.home)
        if is_wechat(final) or 'id="js_content"' in html:
            art = parse_wechat(html, self.clean)
            art.title = entry.title or art.title  # keep the GameRes headline
            art.date = art.date or entry.date
            return art
        soup = soup_of(html)
        node = soup.select_one("#maincontent") or pick_largest(soup, [".contentdiv", "article", "main"])
        content = str(node) if node is not None else readability_content(html)
        meta = page_meta(html, soup)
        h1 = soup.select_one("h1.article-title") or soup.find("h1")
        title = strip_title((h1.get_text(" ", strip=True) if h1 else "") or meta["title"] or entry.title,
                            ["- GameRes游资网", "_GameRes游资网", "| GameRes游资网"])
        author = meta["author"] or ""
        if not author:
            for span in soup.select(".article-meta-item"):
                txt = span.get_text(strip=True)
                if txt.startswith("作者："):
                    author = txt[3:]
        return Article(title=title, content=self.clean(content, final), date=meta["date"] or entry.date,
                       thumb=meta["image"], author=author)
