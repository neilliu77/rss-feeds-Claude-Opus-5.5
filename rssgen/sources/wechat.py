"""Parsing of mp.weixin.qq.com article pages (used when a site links to WeChat articles)."""
from __future__ import annotations

import re

from ..util import first, parse_date
from .base import Article, meta, soup_of

WECHAT_IMG_HOSTS = ("qpic.cn", "qlogo.cn")


def is_wechat(url: str) -> bool:
    return "mp.weixin.qq.com" in (url or "")


def parse_wechat(html: str, clean) -> Article:
    soup = soup_of(html)
    art = Article()
    node = soup.select_one("#js_content") or soup.select_one(".rich_media_content")
    if node is None:
        if "环境异常" in html or "verify" in html[:3000].lower():
            raise RuntimeError("WeChat asked for a captcha")
        raise RuntimeError("WeChat article body not found")
    title = soup.select_one("#activity-name") or soup.select_one(".rich_media_title")
    art.title = first(title.get_text(" ", strip=True) if title else None, meta(soup, "og:title")) or ""
    m = re.search(r'var\s+ct\s*=\s*"?(\d{9,11})"?', html) or re.search(r'create_time\s*[:=]\s*["\']?(\d{9,11})', html)
    if m:
        art.date = parse_date(m.group(1))
    nick = soup.select_one("#js_name")
    m2 = re.search(r'var\s+nickname\s*=\s*(?:htmlDecode\()?"([^"]+)"', html)
    art.author = first(nick.get_text(strip=True) if nick else None, m2.group(1) if m2 else None) or ""
    m3 = re.search(r'var\s+msg_cdn_url\s*=\s*"([^"]+)"', html)
    art.thumb = first(meta(soup, "og:image"), m3.group(1) if m3 else None)
    art.content = clean(node, "https://mp.weixin.qq.com/")
    return art
