"""Temporary diagnostics: do the GIF links now in the feeds play as animations?"""
import io
import requests
from PIL import Image
TESTS = {
 "gamersky": "https://wsrv.nl/?url=https%3A%2F%2Fimggif.gamersky.com%2Fupimg%2Fpic%2F2026%2F10%2F25%2Forigin_202610251554137494.gif&n=-1&default=https%3A%2F%2Fwsrv.nl%2F%3Furl%3Dhttps%253A%252F%252Fimggif.gamersky.com%252Fupimg%252Fpic%252F2026%252F10%252F25%252Forigin_202610251554137494.gif%26output%3Dwebp%26q%3D85",
 "wechat-via-gameres": "https://wsrv.nl/?url=https%3A%2F%2Fmmbiz.qpic.cn%2Fsz_mmbiz_gif%2FmUXhlvFp3ABnlmFsmhXj18mqQiaicM5uVxmQFIZp8d1CdQpKEXguoZnHGxEIUDNUg1BDucrZOUreAEvicE703KtJMHARaj5GvpSF0VqjnJic8ak%2F640%3Fwx_fmt%3Dgif%26from%3Dappmsg&n=-1&default=https%3A%2F%2Fwsrv.nl%2F%3Furl%3Dhttps%253A%252F%252Fmmbiz.qpic.cn%252Fsz_mmbiz_gif%252FmUXhlvFp3ABnlmFsmhXj18mqQiaicM5uVxmQFIZp8d1CdQpKEXguoZnHGxEIUDNUg1BDucrZOUreAEvicE703KtJMHARaj5GvpSF0VqjnJic8ak%252F640%253Fwx_fmt%253Dgif%2526from%253Dappmsg%26output%3Dwebp%26q%3D85",
 "huxiu": "https://wsrv.nl/?url=https%3A%2F%2Fimg.huxiucdn.com%2Farticle%2Fcontent%2F202512%2F03%2F082607115299.gif&n=-1&default=https%3A%2F%2Fwsrv.nl%2F%3Furl%3Dhttps%253A%252F%252Fimg.huxiucdn.com%252Farticle%252Fcontent%252F202512%252F03%252F082607115299.gif%26output%3Dwebp%26q%3D85",
 "fallback-check": "https://wsrv.nl/?url=https%3A%2F%2Fimggif.gamersky.com%2Fupimg%2Fpic%2F2026%2F10%2F25%2Forigin_0000202610251554137494.gif&n=-1&default=https%3A%2F%2Fwsrv.nl%2F%3Furl%3Dhttps%253A%252F%252Fimggif.gamersky.com%252Fupimg%252Fpic%252F2026%252F10%252F25%252Forigin_202610251554137494.gif%26output%3Dwebp%26q%3D85"
}
for name, url in TESTS.items():
    try:
        r = requests.get(url, timeout=90, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"})
        hops = " -> ".join(str(h.status_code) for h in r.history) or "no redirect"
        info = f"HTTP {r.status_code} ({hops}) {r.headers.get('content-type')} {len(r.content)//1024}KB"
        try:
            im = Image.open(io.BytesIO(r.content))
            info += f" | {im.format} {im.size[0]}x{im.size[1]} frames={getattr(im, 'n_frames', 1)}"
        except Exception:
            info += f" | body={r.content[:120]!r}"
    except Exception as e:
        info = f"failed {type(e).__name__}: {e}"
    print(f"::notice title={name}::{info}", flush=True)
