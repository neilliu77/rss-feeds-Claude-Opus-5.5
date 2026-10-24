"""Temporary diagnostic fetcher (will be removed): downloads pages exactly as a GitHub runner sees them.

Reads probe/urls.txt, one request per line:
    name | URL [| follow=REGEX] [| post=k=v&k2=v2] [| referer=URL] [| mobile] [| plain]
Writes probe-out/<name>.body (+ .meta.txt). Lines starting with # are ignored.
"""
import hashlib
import json
import os
import re
import sys
import time
from urllib.parse import urljoin, parse_qsl

from curl_cffi import requests as creq
import requests as preq

MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1")

OUT = "probe-out"
os.makedirs(OUT, exist_ok=True)
session = creq.Session(impersonate="chrome")
plain = preq.Session()
plain.headers["User-Agent"] = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                               "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")


def save(name, resp, err=None, extra=None):
    meta = {"name": name}
    if extra:
        meta.update(extra)
    if err:
        meta["error"] = repr(err)
    if resp is not None:
        body = resp.content or b""
        meta.update({
            "status": resp.status_code,
            "final_url": str(resp.url),
            "headers": {k: v for k, v in resp.headers.items()},
            "bytes": len(body),
            "md5": hashlib.md5(body).hexdigest(),
            "elapsed": getattr(resp, "elapsed", None) and str(resp.elapsed),
        })
        ctype = resp.headers.get("content-type", "")
        if "image" in ctype or "video" in ctype:
            meta["is_image"] = True  # images are only measured, not saved
        else:
            import gzip
            with gzip.open(f"{OUT}/{name}.body.gz", "wb") as f:
                f.write(body)
    with open(f"{OUT}/{name}.meta.txt", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1, default=str)
    print(name, meta.get("status"), meta.get("bytes"), meta.get("final_url"), meta.get("error", ""))


def do(name, url, opts):
    headers = {}
    if "referer" in opts:
        headers["Referer"] = opts["referer"]
    if "mobile" in opts:
        headers["User-Agent"] = MOBILE_UA
    for k, v in opts.items():
        if k.startswith("h:"):
            headers[k[2:]] = v
    sess = plain if "plain" in opts else session
    try:
        if "post" in opts:
            data = dict(parse_qsl(opts["post"], keep_blank_values=True))
            r = sess.post(url, data=data, headers=headers, timeout=40)
        else:
            r = sess.get(url, headers=headers, timeout=40, allow_redirects=True)
        save(name, r, extra={"request_url": url, "opts": opts})
        return r
    except Exception as e:  # noqa
        save(name, None, err=e, extra={"request_url": url, "opts": opts})
        return None


def main():
    lines = open("probe/urls.txt", encoding="utf-8").read().splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            one(line)
        except Exception:
            import traceback
            print("LINE FAILED:", line)
            traceback.print_exc()


def one(line):
    if True:
        parts = [p.strip() for p in line.split(" | ")]
        name, url = parts[0], parts[1]
        opts = {}
        for p in parts[2:]:
            if "=" in p:
                k, v = p.split("=", 1)
                opts[k.strip()] = v.strip()
            else:
                opts[p] = True
        r = do(name, url, opts)
        time.sleep(1.5)
        if r is not None and "follow" in opts:
            try:
                text = r.text
            except Exception:
                text = r.content.decode("utf-8", "replace")
            seen = []
            for m in re.finditer(opts["follow"], text):
                link = urljoin(str(r.url), m.group(1) if m.groups() else m.group(0))
                link = link.replace("\\/", "/")
                if link not in seen:
                    seen.append(link)
            with open(f"{OUT}/{name}.follow.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(seen))
            nfollow = int(opts.get("nfollow", 1))
            for i, link in enumerate(seen[:nfollow]):
                do(f"{name}-f{i+1}", link, {k: v for k, v in opts.items() if k in ("mobile", "plain")})
                time.sleep(1.5)


if __name__ == "__main__":
    import io, contextlib
    buf = io.StringIO()

    class Tee(io.TextIOBase):
        def write(self, x):
            buf.write(x)
            sys.__stdout__.write(x)
            return len(x)

    with contextlib.redirect_stdout(Tee()), contextlib.redirect_stderr(Tee()):
        try:
            main()
        except Exception:
            import traceback
            traceback.print_exc()
    with open(f"{OUT}/_log.txt", "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
