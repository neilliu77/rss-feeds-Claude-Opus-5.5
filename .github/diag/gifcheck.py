"""Temporary diagnostics: which image-proxy settings keep GIF animation, and at what size?"""
import io
from urllib.parse import quote
import requests
from PIL import Image

TESTS = {
 "gamersky-origin": "https://imggif.gamersky.com/upimg/pic/2026/10/25/origin_202610251554137494.gif",
 "wechat": "https://mmbiz.qpic.cn/sz_mmbiz_gif/mUXhlvFp3ABnlmFsmhXj18mqQiaicM5uVxmQFIZp8d1CdQpKEXguoZnHGxEIUDNUg1BDucrZOUreAEvicE703KtJMHARaj5GvpSF0VqjnJic8ak/640?wx_fmt=gif&from=appmsg",
 "huxiu": "https://img.huxiucdn.com/article/content/202512/03/082607115299.gif"
}
VARIANTS = ["", "&n=-1", "&n=-1&output=gif", "&n=-1&w=700", "&n=-1&output=webp&q=85", "&n=-1&output=webp&q=75&w=700"]

for site, src in TESTS.items():
    rows = []
    try:
        orig = requests.get(src, timeout=60)
        im = Image.open(io.BytesIO(orig.content))
        rows.append(f"[original] {len(orig.content)//1024}KB {im.format} {im.size[0]}x{im.size[1]} frames={getattr(im, 'n_frames', 1)}")
    except Exception as e:
        rows.append(f"[original] failed {e}")
    for v in VARIANTS:
        url = f"https://wsrv.nl/?url={quote(src, safe='')}{v}"
        try:
            r = requests.get(url, timeout=90)
            head = f"[{v or 'no params'}] HTTP {r.status_code} {r.headers.get('content-type')} {len(r.content)//1024}KB"
            try:
                im = Image.open(io.BytesIO(r.content))
                rows.append(f"{head} {im.size[0]}x{im.size[1]} frames={getattr(im, 'n_frames', 1)}")
            except Exception:
                rows.append(f"{head} body={r.content[:160]!r}")
        except Exception as e:
            rows.append(f"[{v or 'no params'}] failed {type(e).__name__} {str(e)[:80]}")
    print(f"::notice title={site}::" + " ;; ".join(rows), flush=True)
