"""Temporary diagnostics (will be removed): what does the GitHub runner see right now?"""
import gzip, json, os, sys, time, traceback
sys.path.insert(0, ".")
from rssgen.net import Http
from rssgen.sources import ALL_SOURCES

out = "probe-out"
os.makedirs(out, exist_ok=True)
http = Http()
report = {"ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
raw = [
    ("km-api", "https://www.kmhgame.com/wp-json/wp/v2/posts?per_page=20&_embed=1"),
    ("km-api-fresh", f"https://www.kmhgame.com/wp-json/wp/v2/posts?per_page=5&_fresh={int(time.time())}"),
    ("km-feed", "https://www.kmhgame.com/feed/"),
    ("km-home", "https://www.kmhgame.com/"),
]
for name, url in raw:
    try:
        r = http.session.get(url, timeout=40, headers={"Accept-Language": "zh-CN,zh;q=0.9"})
        report[name] = {"status": r.status_code, "url": str(r.url), "headers": dict(r.headers), "bytes": len(r.content)}
        with gzip.open(f"{out}/{name}.gz", "wb") as f:
            f.write(r.content)
    except Exception as e:  # noqa
        report[name] = {"error": repr(e)}
    time.sleep(1.5)

km = [s for s in ALL_SOURCES if s.id == "kmhgame"][0]
for meth in ("_from_api", "_from_feed", "_from_html"):
    try:
        es = getattr(km, meth)(http)
        report["km" + meth] = [(e.date.isoformat() if e.date else None, e.title[:50], e.link) for e in es[:5]]
    except Exception:  # noqa
        report["km" + meth] = {"error": traceback.format_exc()[-600:]}

for src in ALL_SOURCES:
    try:
        es = src.fetch_list(http)
        report["list:" + src.id] = [(e.date.isoformat() if e.date else None, e.title[:50], e.link) for e in es[:5]]
    except Exception:  # noqa
        report["list:" + src.id] = {"error": traceback.format_exc()[-600:]}

json.dump(report, open(f"{out}/report.json", "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(report, ensure_ascii=False, indent=1, default=str)[:3000])
