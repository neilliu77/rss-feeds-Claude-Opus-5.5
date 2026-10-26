"""Temporary diagnostics: where do GIF animations get lost?"""
import io, json
from urllib.parse import quote
import requests
from PIL import Image

SAMPLES = {
 "gamersky-review": "https://imggif.gamersky.com/upimg/pic/2026/10/25/small_202610251554137494.gif",
 "gameres-25": "https://mmbiz.qpic.cn/sz_mmbiz_gif/mUXhlvFp3ABnlmFsmhXj18mqQiaicM5uVxmQFIZp8d1CdQpKEXguoZnHGxEIUDNUg1BDucrZOUreAEvicE703KtJMHARaj5GvpSF0VqjnJic8ak/640?wx_fmt=gif&from=appmsg",
 "huxiu-collection-400": "https://img.huxiucdn.com/article/content/202512/03/082607115299.gif",
 "lol-dev": "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/082c0658016712124e188f48d8507c3d47614b51-1000x600.gif",
 "gamersky-origin": "https://imggif.gamersky.com/upimg/pic/2026/10/25/origin_202610251554137494.gif"
}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36"}

RESULTS = {}

def probe(label, url, referer=None):
    h = dict(UA)
    if referer:
        h["Referer"] = referer
    try:
        r = requests.get(url, headers=h, timeout=60)
        info = f"HTTP {r.status_code} {r.headers.get('content-type')} {len(r.content)} bytes"
        try:
            im = Image.open(io.BytesIO(r.content))
            info += f" | {im.format} {im.size[0]}x{im.size[1]} frames={getattr(im, 'n_frames', 1)}"
        except Exception as e:
            info += f" | not an image ({type(e).__name__})"
    except Exception as e:
        info = f"failed: {e}"
    site, _, variant = label.partition(" ")
    RESULTS.setdefault(site, []).append(f"[{variant}] {info}")

for site, src in SAMPLES.items():
    q = quote(src, safe="")
    probe(f"{site} original", src)
    probe(f"{site} original+inoreader-referer", src, "https://www.inoreader.com/")
    probe(f"{site} wsrv webp (current)", f"https://wsrv.nl/?url={q}&n=-1&output=webp&q=85")
    probe(f"{site} wsrv keep-format", f"https://wsrv.nl/?url={q}&n=-1")

# GitHub keeps at most 10 annotations per step, so emit one per site
for site, rows in RESULTS.items():
    print(f"::notice title={site}::" + " ;; ".join(rows), flush=True)
