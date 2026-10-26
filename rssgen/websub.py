"""Tell the WebSub hub that some feeds changed, so Inoreader gets the new articles right away.

Usage (run by the workflow right after the updated feeds were pushed):
    python -m rssgen.websub feeds/gamersky-review.xml feeds/kmhgame.xml ...

raw.githubusercontent.com keeps files in its CDN cache for up to 5 minutes. The hub fetches the feed
as soon as it is pinged, so we first wait until the new version is being served everywhere; otherwise
the hub would see the old file and push nothing.
"""
from __future__ import annotations

import hashlib
import sys
import time

import requests

from .feed import HUBS, feed_base_url

CDN_MAX_AGE = 300           # seconds raw.githubusercontent.com may serve a cached copy
MAX_EXTRA_WAIT = 300        # how long to keep checking if the new version still isn't served


def note(msg: str) -> None:
    # "::notice" lines show up as annotations on the workflow run page
    print(f"::notice title=WebSub::{msg}", flush=True)


def served_hash(url: str) -> str | None:
    try:
        r = requests.get(url, timeout=30)
    except requests.RequestException:
        return None
    return hashlib.sha256(r.content).hexdigest() if r.status_code == 200 else None


def main(paths: list[str]) -> int:
    paths = [p for p in paths if p.endswith(".xml")]
    if not paths:
        print("No changed feeds.")
        return 0
    start = time.time()
    base = feed_base_url()
    want = {p: hashlib.sha256(open(p, "rb").read()).hexdigest() for p in paths}
    urls = {p: base + p for p in paths}

    # every CDN node may hold the old copy for up to CDN_MAX_AGE seconds after the push
    time.sleep(max(0.0, start + CDN_MAX_AGE + 15 - time.time()))
    pending = set(paths)
    deadline = time.time() + MAX_EXTRA_WAIT
    while pending:
        pending = {p for p in pending if served_hash(urls[p]) != want[p]}
        if not pending or time.time() > deadline:
            break
        time.sleep(20)
    for p in sorted(pending):
        note(f"{p}: new version still not served after {int(time.time() - start)}s, pinging anyway")

    failed = 0
    for p in paths:
        for hub in HUBS:
            try:
                r = requests.post(hub, data={"hub.mode": "publish", "hub.url": urls[p]}, timeout=30)
                ok = 200 <= r.status_code < 300
                note(f"{p} -> {hub} HTTP {r.status_code}{'' if ok else ' ' + r.text[:200]}")
            except requests.RequestException as e:
                ok = False
                note(f"{p} -> {hub} failed: {e}")
            failed += 0 if ok else 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
