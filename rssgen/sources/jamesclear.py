"""James Clear — 3-2-1 newsletter archive."""
from __future__ import annotations

import datetime as dt
import re
from zoneinfo import ZoneInfo

from .base import Article, Entry, Source, page_meta, pick_largest, readability_content, soup_of

ISSUE_RE = re.compile(r"/3-2-1/([a-z]+)-(\d{1,2})-(\d{4})/?$")
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}
EASTERN = ZoneInfo("America/New_York")


def issue_date(url: str):
    m = ISSUE_RE.search(url)
    if not m or m.group(1) not in MONTHS:
        return None
    try:
        # issues go out on Thursday mornings US Eastern time
        return dt.datetime(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)), 9, 0,
                           tzinfo=EASTERN).astimezone(dt.timezone.utc)
    except ValueError:
        return None


class JamesClear321(Source):
    id = "jamesclear-3-2-1"
    title = "James Clear · 3-2-1 Newsletter"
    home = "https://jamesclear.com/3-2-1"
    description = "3 ideas from me, 2 quotes from others, and 1 question for you — every Thursday."
    language = "en"
    accept_language = "en-US,en;q=0.9"
    list_limit = 15
    keep = 30
    icon = "https://jamesclear.com/favicon.ico"

    def fetch_list(self, http) -> list[Entry]:
        html, final = http.text(self.home, headers=self.headers)
        soup = soup_of(html)
        entries, seen = [], set()
        for a in soup.select("a[href*='/3-2-1/']"):
            href = a["href"].split("?")[0].split("#")[0]
            if href.startswith("/"):
                href = "https://jamesclear.com" + href
            if not ISSUE_RE.search(href) or href in seen:
                continue
            seen.add(href)
            entries.append(Entry(link=href, title=a.get_text(" ", strip=True), date=issue_date(href)))
        entries.sort(key=lambda e: e.date.timestamp() if e.date else 0, reverse=True)
        return entries

    def fetch_article(self, http, entry: Entry) -> Article:
        html, final = http.text(entry.link, headers=self.headers)
        soup = soup_of(html)
        meta = page_meta(html, soup)
        node = pick_largest(soup, [".newsletter__content", ".newsletter-content", ".page__content", ".post__content",
                                   ".entry-content", "article", "main"])
        content = str(node) if node is not None else readability_content(html)
        h1 = soup.find("h1")
        title = (h1.get_text(" ", strip=True) if h1 else "") or entry.title or meta["title"] or ""
        return Article(title=title, content=self.clean(content, final, remove=(
            "form", ".newsletter-signup", ".optin", "[class*='optin']", "[class*='signup']", "[class*='share']")),
            date=entry.date or meta["date"], thumb=meta["image"], author="James Clear")
