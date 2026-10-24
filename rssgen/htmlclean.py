"""Turn messy article HTML into clean, self-contained HTML that RSS readers display well."""
from __future__ import annotations

import html as _html
import re
from urllib.parse import quote, urljoin, urlsplit

from bs4 import BeautifulSoup, Comment, Tag

REMOVE_TAGS = {
    "script", "style", "noscript", "template", "form", "input", "button", "select", "textarea",
    "svg", "canvas", "object", "embed", "link", "meta", "head", "title", "nav", "dialog", "mpvoice",
    "mp-common-profile", "mp-style-type", "qqmusic",
}
KEEP_ATTRS = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
    "iframe": {"src", "width", "height", "allowfullscreen", "frameborder", "allow"},
    "video": {"src", "poster", "controls", "width", "height"},
    "audio": {"src", "controls"},
    "source": {"src", "type"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
    "ol": {"start", "type"},
    "time": {"datetime"},
}
UNWRAP_TAGS = {"font", "span", "center", "o:p", "article", "main"}
EMPTY_REMOVABLE = {"p", "div", "section", "span", "strong", "em", "b", "i", "u", "blockquote", "figure",
                   "header", "font", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol", "a", "figcaption"}
MEDIA_TAGS = ["img", "iframe", "video", "audio", "picture", "hr", "table"]
VIDEO_HOSTS = ("youtube.com", "youtube-nocookie.com", "youtu.be", "player.bilibili.com", "player.vimeo.com",
               "player.youku.com", "v.qq.com")
LAZY_ATTRS = ("data-src", "data-original", "data-lazy-src", "data-actualsrc", "data-original-src", "data-echo",
              "data-lazyload", "data-lazy", "data-url", "_src", "data-ks-lazyload", "data-croporisrc")
PLACEHOLDER_RE = re.compile(
    r"^data:|about:blank|blank\.(gif|png|jpg)|placeholder|loading[^/]*\.(gif|svg|png)|lazy[^/]*\.(gif|png|svg)"
    r"|spacer\.gif|grey\.gif|pixel\.(gif|png)|transparent\.(gif|png)|1x1\.", re.I)
INVALID_XML_RE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿\ud800-\udfff]")
# Public image cache that fetches without a Referer header, so hotlink-protected images load in RSS readers.
# Content images are converted to WebP (much smaller than re-encoded PNG); n=-1 keeps GIF animations.
IMG_PROXY = "https://wsrv.nl/?url={url}&n=-1&output=webp&q=85"
THUMB_PROXY = "https://wsrv.nl/?url={url}&w=640&output=jpg&q=85"


def xml_safe(s: str) -> str:
    return INVALID_XML_RE.sub("", s or "")


def absolute(base: str, url: str | None) -> str | None:
    if not url:
        return None
    url = _html.unescape(url.strip()).replace("\\/", "/")
    if not url or url.startswith(("javascript:", "mailto:", "tel:", "#", "data:")):
        return url if url.startswith(("mailto:", "tel:")) else None
    if url.startswith("//"):
        return "https:" + url
    try:
        return urljoin(base, url)
    except ValueError:
        return None


def proxied(url: str | None, proxy_hosts=(), thumb: bool = False) -> str | None:
    """Route images from hotlink-protected hosts through a public image proxy."""
    if not url or not proxy_hosts or url.startswith(("https://wsrv.nl/", "https://images.weserv.nl/")):
        return url
    host = (urlsplit(url).hostname or "").lower()
    if any(host == h or host.endswith("." + h) for h in proxy_hosts):
        return (THUMB_PROXY if thumb else IMG_PROXY).format(url=quote(url, safe=""))
    return url


def _best_from_srcset(srcset: str) -> str | None:
    best, best_w = None, -1.0
    for part in srcset.split(","):
        bits = part.strip().split()
        if not bits:
            continue
        w = 1.0
        if len(bits) > 1:
            m = re.match(r"([\d.]+)([wx])", bits[1])
            if m:
                w = float(m.group(1))
        if w > best_w:
            best, best_w = bits[0], w
    return best


def image_src(img: Tag) -> str | None:
    for attr in LAZY_ATTRS + ("src",):
        v = img.get(attr)
        if isinstance(v, str) and v.strip() and not PLACEHOLDER_RE.search(v.strip()):
            return v.strip()
    for attr in ("data-srcset", "srcset"):
        v = img.get(attr)
        if isinstance(v, str) and v.strip():
            b = _best_from_srcset(v)
            if b and not PLACEHOLDER_RE.search(b):
                return b
    return None


def _is_hidden(tag: Tag) -> bool:
    style = (tag.get("style") or "").replace(" ", "").lower()
    return "display:none" in style or tag.has_attr("hidden")


def youtube_id(url: str) -> str | None:
    m = re.search(r"(?:youtube(?:-nocookie)?\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|live/)|youtu\.be/)([\w-]{11})", url or "")
    return m.group(1) if m else None


def youtube_embed(video_id: str) -> str:
    return (f'<p><iframe src="https://www.youtube.com/embed/{video_id}" width="640" height="360" '
            f'frameborder="0" allowfullscreen></iframe></p>')


def clean_html(fragment, base_url: str, *, proxy_hosts=(), remove: tuple[str, ...] = (),
               link_text_for_iframes: str = "▶ 打开嵌入内容") -> str:
    """Clean an HTML fragment (str or Tag)."""
    if isinstance(fragment, Tag):
        soup = BeautifulSoup(str(fragment), "lxml")
    else:
        soup = BeautifulSoup(fragment or "", "lxml")
    root = soup.body or soup

    for c in root.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for sel in remove:
        for t in root.select(sel):
            t.decompose()
    for t in root.find_all(list(REMOVE_TAGS)):
        t.decompose()
    for t in root.find_all(True):
        if not t.decomposed and t.attrs is not None and _is_hidden(t):
            t.decompose()

    # images
    for img in root.find_all("img"):
        src = absolute(base_url, image_src(img))
        if not src or not src.startswith("http"):
            img.decompose()
            continue
        img["src"] = proxied(src, proxy_hosts)
    for pic in root.find_all("picture"):
        img = pic.find("img")
        if img:
            pic.replace_with(img)
        else:
            pic.decompose()

    # iframes: keep real video players, turn everything else into a link
    for fr in root.find_all("iframe"):
        src = absolute(base_url, fr.get("data-src") or fr.get("src"))
        if not src:
            fr.decompose()
            continue
        host = (urlsplit(src).hostname or "").lower()
        yid = youtube_id(src)
        if yid:
            fr.attrs = {"src": f"https://www.youtube.com/embed/{yid}", "width": "640", "height": "360",
                        "frameborder": "0", "allowfullscreen": ""}
        elif any(host == h or host.endswith("." + h) for h in VIDEO_HOSTS):
            fr["src"] = src
        else:
            p = soup.new_tag("p")
            a = soup.new_tag("a", href=src)
            a.string = link_text_for_iframes
            p.append(a)
            fr.replace_with(p)

    for v in root.find_all(["video", "audio", "source"]):
        if v.get("src"):
            v["src"] = absolute(base_url, v["src"]) or ""
        if v.get("poster"):
            v["poster"] = absolute(base_url, v["poster"]) or ""

    # links
    for a in root.find_all("a"):
        href = absolute(base_url, a.get("href"))
        if href:
            a["href"] = href
        elif a.has_attr("href"):
            del a["href"]

    # strip attributes
    for t in root.find_all(True):
        allowed = KEEP_ATTRS.get(t.name, set())
        for attr in list(t.attrs):
            if attr not in allowed:
                del t[attr]

    for t in root.find_all(list(UNWRAP_TAGS)):
        t.unwrap()
    for a in root.find_all("a"):
        if not a.get("href"):
            a.unwrap()

    # drop empty blocks (repeat to collapse nesting)
    for _ in range(3):
        changed = False
        for t in root.find_all(list(EMPTY_REMOVABLE)):
            if t.decomposed or t.find(MEDIA_TAGS):
                continue
            if t.get_text(strip=True).replace(" ", "").replace("​", ""):
                continue
            t.decompose()
            changed = True
        if not changed:
            break

    out = root.decode_contents() if root.name in ("body", "[document]") else str(root)
    out = re.sub(r"(\s*<br\s*/?>\s*){3,}", "<br/><br/>", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return xml_safe(out.strip())


def text_of(html_fragment: str, limit: int = 0) -> str:
    text = BeautifulSoup(html_fragment or "", "lxml").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    if limit and len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return text


def first_image(html_fragment: str) -> str | None:
    m = re.search(r'<img[^>]+src="([^"]+)"', html_fragment or "")
    return _html.unescape(m.group(1)) if m else None


def count_images(html_fragment: str) -> int:
    return len(re.findall(r"<img\b", html_fragment or ""))


def escape(s: str) -> str:
    return _html.escape(s or "", quote=True)
