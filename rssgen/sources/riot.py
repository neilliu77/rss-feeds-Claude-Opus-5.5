"""Riot Games news sites (playvalorant.com, leagueoflegends.com).

Both are Next.js sites: every page carries its data in <script id="__NEXT_DATA__">.
The list page holds an ``articleCardGrid`` blade with all cards; an article page is a list of
"blades" (masthead, rich text, accordions, images, embeds ...).
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from ..htmlclean import youtube_embed, youtube_id
from ..util import next_data, walk
from .base import Article, Entry, Source, absolute, escape, page_meta, parse_date, readability_content

SKIP_BLADES = ("riotbar", "card", "carousel", "promo", "footer", "newsletter", "navigation", "cta", "related",
               "social", "share", "rso")


def _url_of(action) -> str | None:
    if not isinstance(action, dict):
        return None
    payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
    return payload.get("url") or action.get("url")


def _media_url(media) -> str | None:
    if isinstance(media, dict):
        if isinstance(media.get("url"), str):
            return media["url"]
        for k in ("image", "thumbnail", "src", "poster"):
            v = media.get(k)
            if isinstance(v, dict) and isinstance(v.get("url"), str):
                return v["url"]
    return None


def _html_of(desc) -> str:
    if isinstance(desc, dict):
        return desc.get("body") or ""
    return desc if isinstance(desc, str) else ""


def _img(url: str, caption: str = "") -> str:
    cap = f"<figcaption>{escape(caption)}</figcaption>" if caption else ""
    return f'<figure><img src="{escape(url)}" alt=""/>{cap}</figure>'


class RiotNews(Source):
    list_limit = 20  # the list page holds the whole archive; only look at the newest cards

    def __init__(self, id: str, title: str, list_url: str, description: str, icon: str | None = None,
                 accept_language: str = "en-US,en;q=0.9", language: str = "en"):
        self.id, self.title, self.home, self.description = id, title, list_url, description
        self.list_url, self.icon = list_url, icon
        self.accept_language, self.language = accept_language, language

    # ----------------------------------------------------------------- list
    def fetch_list(self, http) -> list[Entry]:
        html, final = http.text(self.list_url, headers=self.headers)
        data = next_data(html)
        if not data:
            raise RuntimeError("list page has no __NEXT_DATA__ (site layout changed?)")
        entries: list[Entry] = []
        for d in walk(data):
            title, pub = d.get("title"), d.get("publishedAt")
            url = _url_of(d.get("action"))
            if not (isinstance(title, str) and title.strip() and pub and url):
                continue
            url = urljoin(final, url)
            if url.rstrip("/") == self.list_url.rstrip("/"):
                continue
            yid = (d.get("action", {}).get("payload") or {}).get("youtubeId") or youtube_id(url)
            entries.append(Entry(
                link=f"https://www.youtube.com/watch?v={yid}" if yid else url,
                title=title.strip(), date=parse_date(pub),
                thumb=_media_url(d.get("media")) or _media_url(d.get("imageMedia")),
                summary=_html_of(d.get("description")),
                extra={"youtube": yid}))
        entries.sort(key=lambda e: e.date.timestamp() if e.date else 0, reverse=True)
        return entries

    # -------------------------------------------------------------- article
    def fetch_article(self, http, entry: Entry) -> Article:
        yid = entry.extra.get("youtube") or youtube_id(entry.link)
        if yid:
            return self._video_article(entry, yid)
        host_ok = any(h in entry.link for h in ("leagueoflegends.com", "playvalorant.com", "riotgames.com"))
        if not host_ok:
            return self._external_article(entry)

        html, final = http.text(entry.link, headers=self.headers)
        data = next_data(html)
        page = data.get("props", {}).get("pageProps", {}).get("page") if data else None
        art = Article()
        parts: list[str] = []
        seen: set[str] = set()
        if isinstance(page, dict) and isinstance(page.get("blades"), list):
            for blade in page["blades"]:
                if isinstance(blade, dict):
                    self._blade(blade, parts, seen, art, final)
            art.title = art.title or page.get("title") or ""
            art.date = art.date or parse_date(page.get("displayedPublishDate"))
        content = "\n".join(p for p in parts if p)
        if len(re.sub(r"<[^>]+>", "", content)) < 150:  # unexpected layout: generic extraction
            fallback = readability_content(html)
            if len(re.sub(r"<[^>]+>", "", fallback)) > len(re.sub(r"<[^>]+>", "", content)):
                content = fallback
        meta = page_meta(html)
        art.title = art.title or meta["title"] or entry.title
        art.thumb = art.thumb or entry.thumb or meta["image"]
        art.date = art.date or entry.date or meta["date"]
        art.content = self.clean(content, final)
        return art

    def _blade(self, blade: dict, parts: list[str], seen: set[str], art: Article, base: str) -> None:
        btype = str(blade.get("type", ""))
        low = btype.lower()
        if low == "articlemasthead" or "masthead" in low:
            art.title = blade.get("title") or art.title
            art.date = parse_date(blade.get("publishDate") or blade.get("publishedAt")) or art.date
            cover = _media_url(blade.get("banner")) or _media_url(blade.get("media"))
            names = [a.get("name") or a.get("title") for a in blade.get("authors") or []
                     if isinstance(a, dict) and (a.get("name") or a.get("title"))]
            art.author = ", ".join(names) or art.author
            desc = _html_of(blade.get("description"))
            if desc:
                parts.append(f"<p><em>{desc}</em></p>" if not desc.lstrip().startswith("<") else desc)
            if cover:
                art.thumb = art.thumb or cover
                seen.add(cover)
                parts.append(_img(cover))
            return
        if any(w in low for w in SKIP_BLADES):
            return
        if low == "separator":
            parts.append("<hr/>")
            return
        if low == "articlerichtext":
            parts.append(_html_of(blade.get("richText")))
            return
        if low == "articlerichtextaccordion":
            header = (blade.get("header") or {}).get("title")
            if header:
                parts.append(f"<h3>{escape(header)}</h3>")
            for g in blade.get("groups") or []:
                if isinstance(g, dict):
                    if g.get("label"):
                        parts.append(f"<h4>{escape(g['label'])}</h4>")
                    parts.append(_html_of(g.get("content")))
            return
        # anything else (images, galleries, videos, embeds ...): render what we recognise inside it
        header = blade.get("header") if isinstance(blade.get("header"), dict) else {}
        if header.get("title"):
            parts.append(f"<h3>{escape(header['title'])}</h3>")
        self._render(blade, parts, seen, base)

    def _render(self, node, parts: list[str], seen: set[str], base: str) -> None:
        if isinstance(node, list):
            for x in node:
                self._render(x, parts, seen, base)
            return
        if not isinstance(node, dict):
            return
        ntype = str(node.get("type", "")).lower()
        if ntype == "html" and isinstance(node.get("body"), str):
            parts.append(node["body"])
            return
        for key in ("url", "src", "videoUrl", "embedUrl"):
            v = node.get(key)
            if isinstance(v, str) and youtube_id(v):
                parts.append(youtube_embed(youtube_id(v)))
                return
        yid = node.get("youtubeId") or node.get("videoId")
        if isinstance(yid, str) and re.fullmatch(r"[\w-]{11}", yid):
            parts.append(youtube_embed(yid))
            return
        if ntype == "image" and isinstance(node.get("url"), str):
            if node["url"] not in seen:
                seen.add(node["url"])
                parts.append(_img(node["url"], node.get("caption") if isinstance(node.get("caption"), str) else ""))
            return
        if ntype == "video":
            for s in node.get("sources") or []:
                if isinstance(s, dict) and isinstance(s.get("src"), str):
                    poster = _media_url(node.get("poster")) or ""
                    parts.append(f'<p><video src="{escape(absolute(base, s["src"]) or "")}" '
                                 f'poster="{escape(poster)}" controls></video></p>')
                    return
        for k, v in node.items():
            if k in ("analytics", "action", "authors", "category", "tags", "palette", "colors", "dimensions",
                     "mimeType", "backdrop", "logo", "icon", "socialLinks", "header"):
                continue
            if isinstance(v, (dict, list)):
                self._render(v, parts, seen, base)

    def _video_article(self, entry: Entry, yid: str) -> Article:
        thumb = entry.thumb or f"https://i.ytimg.com/vi/{yid}/hqdefault.jpg"
        desc = entry.summary or ""
        if desc and not desc.lstrip().startswith("<"):
            desc = f"<p>{desc}</p>"
        content = (youtube_embed(yid) + desc +
                   f'<p><a href="https://www.youtube.com/watch?v={yid}">▶ Watch on YouTube</a></p>')
        return Article(title=entry.title, content=self.clean(content, entry.link), date=entry.date, thumb=thumb)

    def _external_article(self, entry: Entry) -> Article:
        desc = entry.summary or ""
        if desc and not desc.lstrip().startswith("<"):
            desc = f"<p>{desc}</p>"
        content = desc + f'<p><a href="{escape(entry.link)}">Read the full post →</a></p>'
        return Article(title=entry.title, content=self.clean(content, entry.link), date=entry.date,
                       thumb=entry.thumb)

